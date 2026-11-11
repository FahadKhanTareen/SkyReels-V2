"""One-time helper: authorize your TikTok account and print the refresh token.

    TIKTOK_CLIENT_KEY=... TIKTOK_CLIENT_SECRET=... TIKTOK_REDIRECT_URI=... python get_token.py

The redirect URI must match one registered on your app in the TikTok developer portal.
"""

import os
import secrets
import sys
from urllib.parse import parse_qs, urlencode, urlparse

import requests

key = os.environ["TIKTOK_CLIENT_KEY"]
secret = os.environ["TIKTOK_CLIENT_SECRET"]
redirect = os.environ["TIKTOK_REDIRECT_URI"]
state = secrets.token_urlsafe(16)

print("1. Open this link, log in to TikTok and approve:\n")
print("https://www.tiktok.com/v2/auth/authorize/?" + urlencode({
    "client_key": key,
    "scope": "user.info.basic,video.publish",
    "response_type": "code",
    "redirect_uri": redirect,
    "state": state,
}))
print("\n2. You will land on your redirect page (it may show an error page, that is fine).")
url = input("   Paste the full address from the browser bar here:\n> ").strip()

query = parse_qs(urlparse(url).query)
if query.get("state", [""])[0] != state:
    sys.exit("State did not match; start again.")
if "code" not in query:
    sys.exit(f"No code in that address: {query}")

resp = requests.post(
    "https://open.tiktokapis.com/v2/oauth/token/",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    data={
        "client_key": key,
        "client_secret": secret,
        "code": query["code"][0],
        "grant_type": "authorization_code",
        "redirect_uri": redirect,
    },
    timeout=30,
).json()
if "refresh_token" not in resp:
    sys.exit(f"TikTok refused: {resp}")
print("\nSave this as the TIKTOK_REFRESH_TOKEN secret (keep it private):\n")
print(resp["refresh_token"])
