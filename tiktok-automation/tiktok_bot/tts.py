"""Text-to-speech for each slide, using the free Microsoft Edge voices."""

import asyncio
import os
import subprocess
from pathlib import Path

VOICE = os.environ.get("TTS_VOICE", "en-US-AndrewNeural")
RATE = os.environ.get("TTS_RATE", "-5%")


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def _silence(path: Path, seconds: float) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-t", f"{seconds:.2f}", "-c:a", "libmp3lame", str(path)],
        check=True,
    )


async def _speak(text: str, path: Path) -> None:
    import edge_tts

    await edge_tts.Communicate(text, VOICE, rate=RATE).save(str(path))


def synthesize(texts: list[str], out_dir: Path) -> list[Path]:
    """One audio file per text. If the voice service is unreachable, the slide gets
    silence sized to its reading time, so a video is still produced."""
    paths = []
    for i, text in enumerate(texts):
        path = out_dir / f"voice_{i:02d}.mp3"
        ok = False
        for attempt in range(3):
            try:
                asyncio.run(_speak(text, path))
                ok = path.exists() and path.stat().st_size > 0
                if ok:
                    break
            except Exception as e:  # network errors from the voice service
                print(f"[tts] attempt {attempt + 1} failed: {type(e).__name__}: {e}")
        if not ok:
            print(f"[tts] no voice for slide {i}; using silence.")
            _silence(path, max(2.0, len(text.split()) / 2.5))
        paths.append(path)
    return paths
