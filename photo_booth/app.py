import argparse
import os
import socket
import uuid

import gradio as gr
import qrcode
from PIL import Image
from PIL import ImageOps

from .styles import STYLES

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

NUM_SCREENS = 5  # welcome, capture, style-select, generating, result


class MockStylizer:
    """CPU-only stand-in for PortraitStylizerPipeline, for exercising the kiosk flow without a GPU/model download."""

    _TINTS = {
        "royal": (255, 215, 0),
        "cyberpunk": (255, 0, 200),
        "anime": (120, 200, 255),
        "watercolor": (200, 220, 255),
        "astronaut": (100, 100, 255),
        "noir": (128, 128, 128),
    }

    def __call__(self, image, style, seed=None, **kwargs):
        img = ImageOps.posterize(image.convert("RGB"), 3)
        tint = Image.new("RGB", img.size, self._TINTS.get(style.id, (200, 200, 200)))
        return Image.blend(img, tint, 0.25)


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def crop_to_square(image: Image.Image) -> Image.Image:
    w, h = image.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return image.crop((left, top, left + side, top + side))


def build_pipeline(args):
    if args.mock:
        return MockStylizer()
    import torch

    from .pipeline import PortraitStylizerPipeline

    return PortraitStylizerPipeline(
        model_id=args.model_id,
        weight_dtype=torch.float16,
        use_ip_adapter=not args.no_ip_adapter,
        offload=args.offload,
    )


KIOSK_CSS = """
.gradio-container { background: radial-gradient(circle at top, #241b3f 0%, #0c0916 70%) !important; }
footer { display: none !important; }
.screen { min-height: 85vh; justify-content: center; align-items: center; text-align: center; }
.kiosk-title { font-size: 3.5em !important; color: #fff; }
.kiosk-btn-xl button { font-size: 2em !important; padding: 1em 2em !important; border-radius: 999px !important; }
.kiosk-btn button { font-size: 1.3em !important; padding: 0.6em 1.4em !important; border-radius: 999px !important; }
.kiosk-style-btn button { font-size: 1.6em !important; padding: 1.2em !important; min-height: 7em !important; white-space: pre-line !important; }
.kiosk-webcam, .kiosk-result { max-width: 640px !important; margin: 0 auto !important; }
.kiosk-qr { max-width: 220px !important; margin: 0 auto !important; }
"""


def build_app(pipeline, public_host: str, public_port: int, idle_reset_seconds: float = 45):
    with gr.Blocks(title="AI Photo Booth") as demo:
        session_photo = gr.State(None)
        idle_timer = gr.Timer(idle_reset_seconds, active=False)

        with gr.Column(visible=True, elem_classes="screen") as screen_welcome:
            gr.Markdown("# ✨ AI Photo Booth ✨", elem_classes="kiosk-title")
            gr.Markdown("Step up, strike a pose, and become a work of art.")
            start_btn = gr.Button("\U0001F449 Tap to Start", elem_classes="kiosk-btn-xl")

        with gr.Column(visible=False, elem_classes="screen") as screen_capture:
            gr.Markdown("## \U0001F4F8 Strike a Pose!")
            cam = gr.Image(
                sources=["webcam"],
                type="pil",
                webcam_options=gr.WebcamOptions(mirror=True),
                elem_classes="kiosk-webcam",
            )
            with gr.Row():
                back_btn_1 = gr.Button("↩ Back", elem_classes="kiosk-btn")
                next_btn_1 = gr.Button("Use This Photo ➜", elem_classes="kiosk-btn-xl")

        with gr.Column(visible=False, elem_classes="screen") as screen_style:
            gr.Markdown("## \U0001F3A8 Choose Your Style")
            style_buttons = []
            with gr.Row():
                for style in STYLES:
                    btn = gr.Button(f"{style.emoji}\n{style.label}", elem_classes="kiosk-style-btn")
                    style_buttons.append((btn, style))
            back_btn_2 = gr.Button("↩ Back", elem_classes="kiosk-btn")

        with gr.Column(visible=False, elem_classes="screen") as screen_generating:
            gr.Markdown("## ✨ Creating Your Masterpiece...")
            gr.Markdown("This takes about a minute. Get ready to be amazed!")

        with gr.Column(visible=False, elem_classes="screen") as screen_result:
            gr.Markdown("## \U0001F389 Your Portrait is Ready!")
            result_img = gr.Image(interactive=False, elem_classes="kiosk-result")
            qr_img = gr.Image(interactive=False, elem_classes="kiosk-qr", label="Scan to download on your phone")
            download_file = gr.File(label="Download")
            restart_btn = gr.Button("\U0001F504 Start Over", elem_classes="kiosk-btn-xl")

        screens = [screen_welcome, screen_capture, screen_style, screen_generating, screen_result]

        def goto(idx):
            return [gr.update(visible=(i == idx)) for i in range(NUM_SCREENS)]

        start_btn.click(
            lambda: goto(1) + [gr.update(active=False)], outputs=screens + [idle_timer]
        )
        back_btn_1.click(
            lambda: goto(0) + [gr.update(active=False)], outputs=screens + [idle_timer]
        )
        back_btn_2.click(
            lambda: goto(1) + [gr.update(active=False)], outputs=screens + [idle_timer]
        )

        def use_photo(photo):
            if photo is None:
                gr.Warning("Please take a photo first!")
                return [gr.update() for _ in screens] + [None]
            return goto(2) + [crop_to_square(photo)]

        next_btn_1.click(use_photo, inputs=[cam], outputs=screens + [session_photo])

        def make_generate_fn(style):
            def _generate(photo):
                if photo is None:
                    gr.Warning("No photo found, please retake it.")
                    yield goto(1) + [gr.update(), gr.update(), gr.update(), gr.update(active=False)]
                    return

                yield goto(3) + [gr.update(), gr.update(), gr.update(), gr.update(active=False)]

                result = pipeline(photo, style, seed=None)

                fname = f"{uuid.uuid4().hex}.png"
                fpath = os.path.join(RESULTS_DIR, fname)
                result.save(fpath)

                download_url = f"http://{public_host}:{public_port}/file={fpath}"
                qr_path = os.path.join(RESULTS_DIR, f"qr_{fname}")
                qrcode.make(download_url).save(qr_path)

                yield goto(4) + [result, qr_path, fpath, gr.update(active=True)]

            return _generate

        for btn, style in style_buttons:
            btn.click(
                make_generate_fn(style),
                inputs=[session_photo],
                outputs=screens + [result_img, qr_img, download_file, idle_timer],
            )

        def restart():
            return goto(0) + [None, gr.update(active=False)]

        restart_btn.click(restart, outputs=screens + [session_photo, idle_timer])
        idle_timer.tick(restart, outputs=screens + [session_photo, idle_timer])

    return demo


def main():
    parser = argparse.ArgumentParser(description="Kiosk-style AI photo booth")
    parser.add_argument("--model_id", type=str, default="stabilityai/stable-diffusion-xl-base-1.0")
    parser.add_argument("--no_ip_adapter", action="store_true", help="Disable IP-Adapter identity conditioning")
    parser.add_argument("--offload", action="store_true", help="Enable CPU offload for low-VRAM GPUs")
    parser.add_argument("--mock", action="store_true", help="Use a fast CPU-only mock stylizer (no GPU/model needed)")
    parser.add_argument("--server_name", type=str, default="0.0.0.0")
    parser.add_argument("--server_port", type=int, default=7863)
    parser.add_argument("--public_host", type=str, default=None, help="Host/IP put in the download QR code")
    parser.add_argument("--idle_reset_seconds", type=float, default=45)
    parser.add_argument("--share", action="store_true")
    args = parser.parse_args()

    pipeline = build_pipeline(args)
    public_host = args.public_host or get_local_ip()

    demo = build_app(pipeline, public_host, args.server_port, args.idle_reset_seconds)
    demo.queue()
    demo.launch(
        server_name=args.server_name,
        server_port=args.server_port,
        share=args.share,
        css=KIOSK_CSS,
        theme=gr.themes.Soft(),
        allowed_paths=[RESULTS_DIR],
    )


if __name__ == "__main__":
    main()
