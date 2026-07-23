import os
import requests
import json
from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("LASTFM_API_KEY")
USERNAME = os.getenv("LASTFM_USERNAME")
API_URL = "https://ws.audioscrobbler.com/2.0/"


def fetch_scrobbles():
    params = {
        "method": "user.getrecenttracks",
        "user": USERNAME,
        "api_key": API_KEY,
        "format": "json"
    }

    response = requests.get(API_URL, params=params)

    print(response.status_code)


if __name__ == "__main__":
    fetch_scrobbles()