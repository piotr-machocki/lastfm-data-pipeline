import os
import requests
import json
import logging
from dotenv import load_dotenv
from src.config import SCROBBLES_JSON, RAW_DIR
from src.lastfm import sign_request


logger = logging.getLogger(__name__)

load_dotenv()

API_KEY = os.getenv("LASTFM_API_KEY")
API_SECRET = os.getenv("LASTFM_API_SECRET")
USERNAME = os.getenv("LASTFM_USERNAME")
SESSION_KEY = os.getenv("LASTFM_SESSION_KEY")
API_URL = "https://ws.audioscrobbler.com/2.0/"

if not all([API_KEY, API_SECRET, USERNAME, SESSION_KEY]):
    logger.error("Missing required Last.fm env vars. Run auth.py first.")
    raise SystemExit(1)


def fetch_scrobbles():
    logger.info("Fetching scrobbles from Last.fm")

    params = {
        "method": "user.getrecenttracks",
        "user": USERNAME,
        "api_key": API_KEY,
        "sk": SESSION_KEY,
        "format": "json",
        "limit": 200,
    }

    api_sig = sign_request(
        {
            key: value
            for key, value in params.items()
            if key != "format"
        },
        API_SECRET,
    )

    params["api_sig"] = api_sig

    try:
        response = requests.get(API_URL, params=params)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error("Request to Last.fm API failed: %s", e)
        raise SystemExit(1)

    data = response.json()

    if "error" in data:
        logger.error(
            "Last.fm API error %s: %s",
            data["error"],
            data.get("message", "Unknown error"),
        )
        raise SystemExit(1)

    if "recenttracks" not in data:
        logger.error("Last.fm API response is missing 'recenttracks'.")
        raise SystemExit(1)

    with open(SCROBBLES_JSON, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    logger.info("Scrobbles saved!")


if __name__ == "__main__":
    from config import setup_logging
    setup_logging()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    fetch_scrobbles()