import os
import sys

import pandas as pd
import psycopg
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

CSV_PATH = "data/processed/scrobbles.csv"
REQUIRED_COLUMNS = {"artist", "track", "album", "timestamp"}


def load_scrobbles() -> None:
    df = pd.read_csv(CSV_PATH)

    df = df.where(pd.notnull(df), None)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"scrobbles.csv is missing required columns: {missing}")

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    if df["timestamp"].isna().any():
        raise ValueError("Invalid timestamps found")

    records = list(
        df[["artist", "track", "album", "timestamp"]]
        .itertuples(index=False, name=None)
    )

    try:
        with psycopg.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS scrobbles (
                        id SERIAL PRIMARY KEY,
                        artist TEXT,
                        track TEXT,
                        album TEXT,
                        timestamp TIMESTAMP
                    );
                """)

                cursor.executemany(
                    """
                    INSERT INTO scrobbles (artist, track, album, timestamp)
                    VALUES (%s, %s, %s, %s);
                    """,
                    records,
                )

    except psycopg.Error as e:
        print(f"Database error while loading scrobbles: {e}", file=sys.stderr)
        raise SystemExit(1)

    print(f"Loaded {len(records)} scrobbles successfully!")


if __name__ == "__main__":
    load_scrobbles()