import os
import requests
import json
import hashlib
from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("LASTFM_API_KEY")
API_SECRET = os.getenv("LASTFM_API_SECRET")
USERNAME = os.getenv("LASTFM_USERNAME")
SESSION_KEY = os.getenv("LASTFM_SESSION_KEY")
API_URL = "https://ws.audioscrobbler.com/2.0/"


def fetch_scrobbles():
    signature_string = (
    f"api_key{API_KEY}"
    f"methoduser.getrecenttracks"
    f"sk{SESSION_KEY}"
    f"user{USERNAME}"
    f"{API_SECRET}"
)

    api_sig = hashlib.md5(
        signature_string.encode("utf-8")
    ).hexdigest()

    params = {
    "method": "user.getrecenttracks",
    "user": USERNAME,
    "api_key": API_KEY,
    "sk": SESSION_KEY,
    "api_sig": api_sig,
    "format": "json"
}

    response = requests.get(API_URL, params=params)

    data = response.json()

    with open("data/raw/scrobbles.json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    print("Scrobbles saved!")


if __name__ == "__main__":
    fetch_scrobbles()