"""Writes the short motivational script for one video."""

import json
import os
import random
from pathlib import Path

from pydantic import BaseModel

DATA = Path(__file__).resolve().parent.parent / "data"
HISTORY = DATA / "history.json"
FALLBACK = DATA / "fallback_scripts.json"

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5-5")

SYSTEM = """You write scripts for short vertical motivational videos (15-25 seconds).
Each video is a spoken hook followed by 3-5 short spoken lines, shown on screen one at a time.

Write original lines in plain, direct language. No attributed quotes from real people,
no cliches like "hustle" or "grind", no emojis, no hashtags inside the spoken text.
Every line must be under 14 words so it fits on screen and is easy to say aloud.
The hook should make someone stop scrolling. The last line should land the idea.
The caption is one short sentence for the post description. Give 4-6 hashtags without the # sign."""


class VideoScript(BaseModel):
    hook: str
    lines: list[str]
    caption: str
    hashtags: list[str]


def load_history() -> list[dict]:
    try:
        return json.loads(HISTORY.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_history(script: VideoScript, extra: dict | None = None) -> None:
    history = load_history()
    history.append({**script.model_dump(), **(extra or {})})
    HISTORY.write_text(json.dumps(history[-200:], indent=2) + "\n")


def _from_claude(recent_hooks: list[str]) -> VideoScript | None:
    import anthropic

    avoid = "\n".join(f"- {h}" for h in recent_hooks) or "(none yet)"
    client = anthropic.Anthropic()
    try:
        response = client.beta.messages.parse(
            model=MODEL,
            max_tokens=4000,
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": "Write one new video script. Pick a fresh theme; these hooks "
                    f"were used recently, so do not repeat their ideas:\n{avoid}",
                }
            ],
            output_format=VideoScript,
        )
    except anthropic.APIError as e:
        print(f"[script] Claude request failed ({e}); using a bundled script.")
        return None
    if response.stop_reason != "end_turn" or response.parsed_output is None:
        print(f"[script] Claude stopped with {response.stop_reason}; using a bundled script.")
        return None
    return response.parsed_output


def _from_bundle(recent_hooks: list[str]) -> VideoScript:
    scripts = json.loads(FALLBACK.read_text())
    unused = [s for s in scripts if s["hook"] not in recent_hooks] or scripts
    return VideoScript(**random.choice(unused))


def write_script() -> VideoScript:
    recent = [h["hook"] for h in load_history()[-30:]]
    script = None
    if os.environ.get("ANTHROPIC_API_KEY"):
        script = _from_claude(recent)
    else:
        print("[script] ANTHROPIC_API_KEY not set; using a bundled script.")
    script = script or _from_bundle(recent)
    script.lines = [line.strip() for line in script.lines if line.strip()][:6]
    script.hashtags = [t.lstrip("#").replace(" ", "") for t in script.hashtags][:6]
    return script
