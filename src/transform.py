import json
import pandas as pd
from datetime import datetime, timezone
from config import SCROBBLES_JSON, SCROBBLES_CSV


def transform_scrobbles():
    with open(SCROBBLES_JSON, "r", encoding="utf-8") as file:
        data = json.load(file)

    tracks = data["recenttracks"]["track"]
    
    if isinstance(tracks, dict):
        tracks = [tracks]

    clean_tracks = []

    for track in tracks:
        # skip currently playing track
        if "@attr" in track:
            continue

        clean_track = {
            "artist": track["artist"]["#text"],
            "album": track["album"]["#text"],
            "track": track["name"],
            "timestamp": datetime.fromtimestamp(
    int(track["date"]["uts"]),
    tz=timezone.utc,
)
    
        }

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