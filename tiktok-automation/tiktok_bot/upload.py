"""Uploads a video with the official TikTok Content Posting API (direct post, file upload).

Docs: https://developers.tiktok.com/doc/content-posting-api-reference-direct-post
"""

import os
import time
from pathlib import Path

import requests

API = "https://open.tiktokapis.com/v2"
CHUNK = 10 * 1024 * 1024  # used only for files above 64 MB
SINGLE_UPLOAD_MAX = 64 * 1024 * 1024


class TikTokError(RuntimeError):
    pass


def _check(resp: requests.Response) -> dict:
    try:
        body = resp.json()
    except ValueError:
        raise TikTokError(f"HTTP {resp.status_code}: {resp.text[:300]}")
    err = body.get("error") or {}
    if isinstance(err, str):  # the OAuth endpoint uses a flat error shape
        raise TikTokError(f"{err}: {body.get('error_description')}")
    if resp.status_code >= 400 or err.get("code", "ok") != "ok":
        raise TikTokError(f"HTTP {resp.status_code} {err.get('code')}: {err.get('message')}")
    return body


def refresh_access_token() -> tuple[str, str]:
    """Exchanges the long-lived refresh token for an access token.
    Returns (access_token, refresh_token); TikTok may rotate the refresh token."""
    resp = requests.post(
        f"{API}/oauth/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": os.environ["TIKTOK_CLIENT_KEY"],
            "client_secret": os.environ["TIKTOK_CLIENT_SECRET"],
            "grant_type": "refresh_token",
            "refresh_token": os.environ["TIKTOK_REFRESH_TOKEN"],
        },
        timeout=30,
    )
    body = _check(resp)
    if "access_token" not in body:
        raise TikTokError(f"No access token in response: {body}")
    return body["access_token"], body.get("refresh_token", os.environ["TIKTOK_REFRESH_TOKEN"])


def upload(video: Path, title: str, access_token: str) -> str:
    """Posts the video and returns TikTok's publish_id."""
    auth = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json; charset=UTF-8"}

    creator = _check(requests.post(f"{API}/post/publish/creator_info/query/", headers=auth, timeout=30))["data"]
    allowed = creator.get("privacy_level_options", [])
    privacy = os.environ.get("TIKTOK_PRIVACY", "SELF_ONLY")
    if privacy not in allowed:
        raise TikTokError(
            f"Privacy level {privacy} is not available for this account/app (allowed: {allowed}). "
            "Apps that have not passed TikTok's audit can only post as SELF_ONLY."
        )

    size = video.stat().st_size
    if size <= SINGLE_UPLOAD_MAX:
        chunk_size, chunks = size, 1
    else:
        chunk_size, chunks = CHUNK, size // CHUNK  # the last chunk carries the remainder

    init = _check(requests.post(
        f"{API}/post/publish/video/init/",
        headers=auth,
        json={
            "post_info": {
                "title": title[:2200],
                "privacy_level": privacy,
                "disable_comment": bool(creator.get("comment_disabled", False)),
                "disable_duet": bool(creator.get("duet_disabled", False)),
                "disable_stitch": bool(creator.get("stitch_disabled", False)),
                "is_aigc": True,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": size,
                "chunk_size": chunk_size,
                "total_chunk_count": chunks,
            },
        },
        timeout=30,
    ))["data"]

    with video.open("rb") as f:
        for i in range(chunks):
            start = i * chunk_size
            end = size - 1 if i == chunks - 1 else start + chunk_size - 1
            f.seek(start)
            put = requests.put(
                init["upload_url"],
                headers={"Content-Type": "video/mp4", "Content-Range": f"bytes {start}-{end}/{size}"},
                data=f.read(end - start + 1),
                timeout=600,
            )
            if put.status_code not in (200, 201, 206):
                raise TikTokError(f"Chunk {i + 1}/{chunks} failed: HTTP {put.status_code} {put.text[:300]}")

    publish_id = init["publish_id"]
    for _ in range(30):  # wait up to ~5 minutes for TikTok to process the video
        time.sleep(10)
        status = _check(requests.post(
            f"{API}/post/publish/status/fetch/", headers=auth, json={"publish_id": publish_id}, timeout=30,
        ))["data"]
        state = status.get("status")
        print(f"[upload] status: {state}")
        if state == "PUBLISH_COMPLETE":
            return publish_id
        if state == "FAILED":
            raise TikTokError(f"TikTok rejected the video: {status.get('fail_reason')}")
    print("[upload] still processing after 5 minutes; check the TikTok app.")
    return publish_id
