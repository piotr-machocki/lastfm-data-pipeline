import os
import random
import time
import requests
import json
import logging
from dotenv import load_dotenv
from src.config import SCROBBLES_JSON, RAW_DIR


logger = logging.getLogger(__name__)

load_dotenv()

API_KEY = os.getenv("LASTFM_API_KEY")
USERNAME = os.getenv("LASTFM_USERNAME")
API_URL = "https://ws.audioscrobbler.com/2.0/"

if not all([API_KEY, USERNAME]):
    logger.error("Missing required Last.fm environment variables.")
    raise SystemExit(1)

# Only used by the full-history fetch 
RATE_LIMIT_DELAY = 0.25  # seconds between requests
MAX_RETRIES = 5
RETRY_BASE_DELAY = 2.0  # seconds, doubles each retry


def fetch_scrobbles(since=None, full_history=False):
    logger.info("Fetching scrobbles from Last.fm")

    if full_history:
        _fetch_full_history()
        return

    all_tracks = []
    page = 1
    total_pages = 1

    while page <= total_pages:
        params = {
            "method": "user.getrecenttracks",
            "user": USERNAME,
            "api_key": API_KEY,
            "format": "json",
            "limit": 200,
            "page": page,
        }

        if since is not None:
            params["from"] = since

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

        recenttracks = data["recenttracks"]
        tracks = recenttracks.get("track", [])

        if isinstance(tracks, dict):
            tracks = [tracks]

        all_tracks.extend(tracks)

        total_pages = int(recenttracks.get("@attr", {}).get("totalPages", 1))
        logger.info("Fetched page %d/%d (%d tracks)", page, total_pages, len(tracks))

        page += 1

        if since is None and not full_history:
            logger.info("No 'since' cursor and full_history=False — fetching newest page only")
            break

    with open(SCROBBLES_JSON, "w", encoding="utf-8") as file:
        json.dump({"recenttracks": {"track": all_tracks}}, file, indent=4, ensure_ascii=False)

    logger.info("Saved %d scrobbles total", len(all_tracks))


# Full-history path: rate-limited, retried, and checkpointed so a run that
# gets interrupted partway through doesn't have to restart from page 1.

def _checkpoint_paths():
    base = SCROBBLES_JSON.parent
    return base / "scrobbles_checkpoint.jsonl", base / "scrobbles_checkpoint_state.json"


def _load_checkpoint_state(state_path):
    if not state_path.exists():
        return None
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning("Checkpoint state file is unreadable; starting over")
        return None


def _save_checkpoint_state(state_path, next_page, total_pages):
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump({"next_page": next_page, "total_pages": total_pages}, f)


def _request_page(params, max_retries=MAX_RETRIES, base_delay=RETRY_BASE_DELAY):
    """Fetch one page with retry/backoff on transient errors and Last.fm rate limiting (error 29)."""
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(API_URL, params=params, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            if attempt == max_retries:
                logger.error("Request to Last.fm API failed after %d attempts: %s", max_retries, e)
                raise SystemExit(1)
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            logger.warning(
                "Request failed (attempt %d/%d): %s - retrying in %.1fs",
                attempt, max_retries, e, delay,
            )
            time.sleep(delay) 
            continue

        data = response.json()

        if "error" in data:
            if data["error"] == 29 and attempt < max_retries:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning("Rate limited by Last.fm (error 29) — retrying in %.1fs", delay)
                time.sleep(delay)
                continue
            logger.error(
                "Last.fm API error %s: %s",
                data["error"],
                data.get("message", "Unknown error"),
            )
            raise SystemExit(1)

        return data

    logger.error("Exhausted retries without a successful response")
    raise SystemExit(1)


def _fetch_full_history():
    checkpoint_path, state_path = _checkpoint_paths()
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    state = _load_checkpoint_state(state_path)

    if state:
        page = state["next_page"]
        total_pages = state["total_pages"]
        logger.info("Resuming full-history fetch from page %d/%d", page, total_pages)
        checkpoint_mode = "a"
    else:
        page = 1
        total_pages = 1
        checkpoint_mode = "w"

    with open(checkpoint_path, checkpoint_mode, encoding="utf-8") as checkpoint_file:
        while page <= total_pages:
            params = {
                "method": "user.getrecenttracks",
                "user": USERNAME,
                "api_key": API_KEY,
                "format": "json",
                "limit": 200,
                "page": page,
            }

            data = _request_page(params)
            recenttracks = data.get("recenttracks")

            if recenttracks is None:
                logger.error("Last.fm API response is missing 'recenttracks'.")
                raise SystemExit(1)

            tracks = recenttracks.get("track", [])
            if isinstance(tracks, dict):
                tracks = [tracks]

            for track in tracks:
                checkpoint_file.write(json.dumps(track, ensure_ascii=False) + "\n")
            checkpoint_file.flush()

            total_pages = int(recenttracks.get("@attr", {}).get("totalPages", 1))
            logger.info("Fetched page %d/%d (%d tracks)", page, total_pages, len(tracks))

            page += 1
            _save_checkpoint_state(state_path, page, total_pages)

            if page <= total_pages:
                time.sleep(RATE_LIMIT_DELAY)

    # All pages fetched - assemble the final output the rest of the pipeline expects.
    all_tracks = []
    with open(checkpoint_path, "r", encoding="utf-8") as checkpoint_file:
        for line in checkpoint_file:
            line = line.strip()
            if line:
                all_tracks.append(json.loads(line))

    with open(SCROBBLES_JSON, "w", encoding="utf-8") as file:
        json.dump({"recenttracks": {"track": all_tracks}}, file, indent=4, ensure_ascii=False)

    checkpoint_path.unlink(missing_ok=True)
    state_path.unlink(missing_ok=True)

    logger.info("Saved %d scrobbles total (full history)", len(all_tracks))


if __name__ == "__main__":
    import argparse
    from src.config import setup_logging
    from src.load import get_last_timestamp

    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--incremental",
        action="store_true",
        help="Fetch scrobbles since the last timestamp stored in the database",
    )
    group.add_argument(
        "--full-history",
        action="store_true",
        help="Fetch the complete scrobble history",
    )

    args = parser.parse_args()

    setup_logging()
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    since = get_last_timestamp() if args.incremental else None

    fetch_scrobbles(
        since=since,
        full_history=args.full_history,
    )