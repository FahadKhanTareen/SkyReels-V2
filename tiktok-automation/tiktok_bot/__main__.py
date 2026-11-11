"""Make one video and (optionally) upload it:  python -m tiktok_bot [--upload]"""

import argparse
import os
import sys
import time
from pathlib import Path

from . import render, script, tts, upload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upload", action="store_true", help="post the video to TikTok")
    parser.add_argument("--out", default="out", help="output directory")
    args = parser.parse_args()

    out = Path(args.out) / time.strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)

    video_script = script.write_script()
    texts = [video_script.hook, *video_script.lines]
    print("[script]", " / ".join(texts))

    audio = tts.synthesize(texts, out)
    music = Path(os.environ["MUSIC_FILE"]) if os.environ.get("MUSIC_FILE") else None
    video = render.render(texts, audio, out, music)
    title = f"{video_script.caption} " + " ".join(f"#{t}" for t in video_script.hashtags)
    (out / "caption.txt").write_text(title + "\n")
    print(f"[render] {video} ({tts.duration(video):.1f}s)")
    print(f"[caption] {title}")

    publish_id = None
    if args.upload:
        access_token, refresh_token = upload.refresh_access_token()
        if refresh_token != os.environ["TIKTOK_REFRESH_TOKEN"]:
            # Picked up by the workflow, which stores it as the new secret.
            Path(os.environ.get("NEW_REFRESH_TOKEN_FILE", out / "new_refresh_token")).write_text(refresh_token)
            print("[upload] TikTok issued a new refresh token.")
        publish_id = upload.upload(video, title, access_token)
        print(f"[upload] done, publish_id={publish_id}")

    script.save_history(video_script, {"date": time.strftime("%Y-%m-%d"), "publish_id": publish_id})
    return 0


if __name__ == "__main__":
    sys.exit(main())
