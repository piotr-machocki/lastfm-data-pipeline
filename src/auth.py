import os
import requests
import hashlib
from dotenv import load_dotenv
from pathlib import Path


load_dotenv()

API_KEY = os.getenv("LASTFM_API_KEY")
API_SECRET = os.getenv("LASTFM_API_SECRET")
USERNAME = os.getenv("LASTFM_USERNAME")

API_URL = "https://ws.audioscrobbler.com/2.0/"


def get_token():
    params = {
        "method": "auth.getToken",
        "api_key": API_KEY,
        "format": "json"
    }

    response = requests.get(API_URL, params=params)

    data = response.json()

    token = data["token"]

    print("\nOpen this URL in your browser:")
    print(
        f"https://www.last.fm/api/auth/?api_key={API_KEY}&token={token}"
    )

    return token


def save_session_key(session_key):
    env_path = Path(".env")

    lines = []

    if env_path.exists():
        lines = env_path.read_text().splitlines()

    updated = False

    for i, line in enumerate(lines):
        if line.startswith("LASTFM_SESSION_KEY="):
            lines[i] = f"LASTFM_SESSION_KEY={session_key}"
            updated = True

    if not updated:
        lines.append(f"LASTFM_SESSION_KEY={session_key}")

    env_path.write_text("\n".join(lines) + "\n")

    print("Session key saved to .env")


def get_session(token):
    params = {
        "method": "auth.getSession",
        "api_key": API_KEY,
        "token": token,
        "format": "json"
    }

    signature_string = (
        f"api_key{API_KEY}"
        f"methodauth.getSession"
        f"token{token}"
        f"{API_SECRET}"
    )

    api_sig = hashlib.md5(
        signature_string.encode("utf-8")
    ).hexdigest()

    params["api_sig"] = api_sig

    response = requests.get(API_URL, params=params)

    data = response.json()

    print("\nSession response:")
    print(data)

    session_key = data["session"]["key"]

    save_session_key(session_key)


if __name__ == "__main__":
    token = get_token()

    input(
        "\nAfter authorizing the application, press ENTER to continue..."
    )

    get_session(token)