import json
import sys
import pandas as pd
from datetime import datetime, timezone
from config import SCROBBLES_JSON, SCROBBLES_CSV


def transform_scrobbles():
    try:
        with open(SCROBBLES_JSON, "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Input file not found: {SCROBBLES_JSON}", file=sys.stderr)
        raise SystemExit(1)
    except json.JSONDecodeError as e:
        print(f"Malformed JSON in {SCROBBLES_JSON}: {e}", file=sys.stderr)
        raise SystemExit(1)

    try:
        tracks = data["recenttracks"]["track"]
    except KeyError:
        print(f"{SCROBBLES_JSON} is missing 'recenttracks.track'.", file=sys.stderr)
        raise SystemExit(1)

    if isinstance(tracks, dict):
        tracks = [tracks]

    clean_tracks = []

    for track in tracks:
        if "@attr" in track:
            continue

        try:
            clean_track = {
                "artist": track["artist"]["#text"],
                "album": track["album"]["#text"],
                "track": track["name"],
                "timestamp": datetime.fromtimestamp(
                    int(track["date"]["uts"]),
                    tz=timezone.utc,
                )
            }
        except (KeyError, TypeError, ValueError) as e:
            print(f"Skipping malformed track record: {e}", file=sys.stderr)
            continue

        clean_tracks.append(clean_track)

    df = pd.DataFrame(clean_tracks)

    df.to_csv(
        SCROBBLES_CSV,
        index=False,
        encoding="utf-8"
    )

    print(f"Saved {len(df)} transformed tracks")


if __name__ == "__main__":
    transform_scrobbles()