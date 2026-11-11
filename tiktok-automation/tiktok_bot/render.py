"""Renders slides with Pillow and assembles the vertical video with ffmpeg."""

import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .tts import duration

W, H = 1080, 1920
FPS = 30
PAUSE = 0.35  # seconds of breathing room after each spoken line

PALETTES = [
    ((15, 23, 42), (88, 28, 135)),
    ((12, 20, 30), (14, 116, 144)),
    ((30, 16, 12), (180, 83, 9)),
    ((10, 25, 20), (21, 128, 61)),
    ((24, 12, 28), (190, 24, 93)),
    ((8, 12, 30), (37, 99, 235)),
]

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    raise RuntimeError("No bold font found. Install fonts-dejavu-core.")


def _background(top: tuple, bottom: tuple, seed: int) -> Image.Image:
    """Vertical gradient with a few soft glowing blobs for depth."""
    rng = random.Random(seed)
    strip = Image.new("RGB", (1, H))
    for y in range(H):
        t = y / (H - 1)
        strip.putpixel((0, y), tuple(round(top[c] + (bottom[c] - top[c]) * t) for c in range(3)))
    img = strip.resize((W, H))
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    draw = ImageDraw.Draw(glow)
    for _ in range(4):
        r = rng.randint(250, 520)
        x, y = rng.randint(0, W), rng.randint(0, H)
        shade = rng.randint(30, 70)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(shade, shade, shade))
    glow = glow.filter(ImageFilter.GaussianBlur(180))
    return Image.blend(img, Image.composite(Image.new("RGB", (W, H), (255, 255, 255)), img, glow.convert("L")), 0.6)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    lines, current = [], ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _slide(bg: Image.Image, text: str, index: int, total: int, is_hook: bool, path: Path) -> None:
    img = bg.copy()
    draw = ImageDraw.Draw(img)
    max_width = W - 180
    size = 104 if is_hook else 88
    while True:  # shrink until the text block fits the safe area
        font = _font(size)
        lines = _wrap(draw, text.upper() if is_hook else text, font, max_width)
        line_h = int(size * 1.3)
        if len(lines) * line_h <= 900 or size <= 48:
            break
        size -= 6
    y = (H - len(lines) * line_h) // 2 - 60
    for line in lines:
        x = (W - draw.textlength(line, font=font)) // 2
        draw.text((x + 4, y + 5), line, font=font, fill=(0, 0, 0))
        draw.text((x, y), line, font=font, fill=(255, 221, 87) if is_hook else (255, 255, 255))
        y += line_h
    # progress dots, kept above TikTok's bottom UI area
    dot, gap = 16, 36
    start = (W - (total - 1) * gap) // 2
    for i in range(total):
        cx, cy = start + i * gap, H - 420
        draw.ellipse((cx - dot // 2, cy - dot // 2, cx + dot // 2, cy + dot // 2),
                     fill=(255, 255, 255) if i == index else (120, 120, 130))
    img.save(path)


def render(texts: list[str], audio: list[Path], out_dir: Path, music: Path | None = None) -> Path:
    """texts[0] is the hook. One slide per text, timed to its voice clip."""
    top, bottom = random.choice(PALETTES)
    bg = _background(top, bottom, seed=random.randrange(10**6))
    segments = []
    for i, (text, voice) in enumerate(zip(texts, audio)):
        png = out_dir / f"slide_{i:02d}.png"
        _slide(bg, text, i, len(texts), i == 0, png)
        length = duration(voice) + PAUSE
        seg = out_dir / f"seg_{i:02d}.mp4"
        fade_out = max(0.0, length - 0.25)
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error",
             "-loop", "1", "-framerate", str(FPS), "-t", f"{length:.3f}", "-i", str(png),
             "-i", str(voice),
             "-filter_complex",
             # slow push-in so the frame is never static
             f"[0:v]scale={W * 2}:{H * 2},zoompan=z='1+0.04*on/{int(length * FPS)}':"
             f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS},"
             f"fade=t=in:st=0:d=0.25,fade=t=out:st={fade_out:.3f}:d=0.25,format=yuv420p[v];"
             f"[1:a]apad,atrim=0:{length:.3f},aresample=44100[a]",
             "-map", "[v]", "-map", "[a]", "-t", f"{length:.3f}",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
             "-c:a", "aac", "-b:a", "160k", "-ac", "2", str(seg)],
            check=True,
        )
        segments.append(seg)

    concat = out_dir / "concat.txt"
    concat.write_text("".join(f"file '{s.resolve()}'\n" for s in segments))
    final = out_dir / "video.mp4"
    joined = out_dir / "joined.mp4" if music else final
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat),
         "-c", "copy", "-movflags", "+faststart", str(joined)],
        check=True,
    )
    if music:
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(joined), "-stream_loop", "-1", "-i", str(music),
             "-filter_complex", "[1:a]volume=0.12[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
             "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
             "-movflags", "+faststart", str(final)],
            check=True,
        )
    return final
