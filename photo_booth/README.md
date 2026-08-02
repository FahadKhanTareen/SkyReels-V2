# AI Photo Booth

A kiosk-style photo booth, inspired by [Musavir AI](https://musavir.ai/musavir-v2)'s
event photo booths: a visitor takes a selfie, picks a style, and gets back a
stylized AI portrait a few seconds later, downloadable via a QR code.

It's a standalone feature built on top of this repo — it does not use the
SkyReels-V2 video models. Portraits are generated with an SDXL img2img
pipeline (+ IP-Adapter for identity preservation), since that's a much
lighter/faster fit for single-image stylization than SkyReels-V2's
autoregressive video diffusion models.

## Install

```shell
pip install -r photo_booth/requirements.txt
```

(Uses `diffusers`/`torch`, already required by the main repo.)

## Run

Try the kiosk flow instantly, no GPU or model download required:

```shell
python -m photo_booth.app --mock
```

Run it for real on a GPU machine:

```shell
python -m photo_booth.app --server_port 7863
```

Open `http://<kiosk-ip>:7863` in a fullscreen kiosk browser (e.g. Chrome
`--kiosk` mode). Visitors: tap to start → take a selfie → pick a style →
wait for the portrait → scan the QR code to download it to their phone →
booth resets automatically after `--idle_reset_seconds` (default 45s).

### Useful flags

| Flag | Description |
| --- | --- |
| `--mock` | Skip the diffusion pipeline, use a fast CPU-only placeholder stylizer (for UI/dev testing) |
| `--model_id` | Base SDXL checkpoint to use (default `stabilityai/stable-diffusion-xl-base-1.0`) |
| `--no_ip_adapter` | Disable IP-Adapter identity conditioning |
| `--offload` | Enable CPU offload for lower-VRAM GPUs |
| `--public_host` | Host/IP to embed in the download QR code (auto-detected from the local network by default) |
| `--idle_reset_seconds` | How long the result screen stays up before auto-resetting |

## Layout

- `styles.py` — the style presets shown in the kiosk (prompt, strength, guidance scale per style)
- `pipeline.py` — `PortraitStylizerPipeline`, the SDXL img2img + IP-Adapter wrapper
- `app.py` — the Gradio kiosk UI (welcome → capture → style select → generating → result) and CLI entrypoint

Generated portraits and their QR codes are written to `photo_booth/results/`
(git-ignored).

## Adding a new style

Add a `Style(...)` entry to `STYLES` in `styles.py` with an `id`, `label`,
`emoji`, and stylization `prompt`; it shows up in the kiosk automatically.
