import json
import pandas as pd


def transform_scrobbles():
    with open("data/raw/scrobbles.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    tracks = data["recenttracks"]["track"]

    clean_tracks = []

    for track in tracks:
        # skip currently playing track
        if "@attr" in track:
            continue

        clean_track = {
            "artist": track["artist"]["#text"],
            "album": track["album"]["#text"],
            "track": track["name"],
            "url": track["url"]
        }

        clean_tracks.append(clean_track)

    df = pd.DataFrame(clean_tracks)

    df.to_csv(
        "data/processed/scrobbles.csv",
        index=False,
        encoding="utf-8"
    )

    print(f"Saved {len(df)} transformed tracks")


if __name__ == "__main__":
    transform_scrobbles()