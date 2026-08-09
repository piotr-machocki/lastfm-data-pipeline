import os
import sys

import pandas as pd
import psycopg
from dotenv import load_dotenv

from config import VALIDATED_CSV

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
    print("Missing required DB environment variables. Check your .env file.", file=sys.stderr)
    raise SystemExit(1)

REQUIRED_COLUMNS = {"artist", "track", "album", "timestamp"}


def load_scrobbles() -> None:
    try:
        df = pd.read_csv(VALIDATED_CSV)
    except FileNotFoundError:
        print(f"Input file not found: {VALIDATED_CSV}", file=sys.stderr)
        raise SystemExit(1)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        print(
            f"{VALIDATED_CSV} is missing required columns: {missing}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    df = df[["artist", "track", "album", "timestamp"]]
    df = df.astype(object).where(df.notna(), None)

    records = list(df.itertuples(index=False, name=None))

    if not records:
        print("No records to insert.")
        return

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
                        id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        artist TEXT NOT NULL,
                        track TEXT NOT NULL,
                        album TEXT,
                        timestamp TIMESTAMP NOT NULL,
                        UNIQUE (artist, track, timestamp)
                    );
                """)

                cursor.executemany(
                    """
                    INSERT INTO scrobbles (artist, track, album, timestamp)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (artist, track, timestamp) DO NOTHING
                    RETURNING id;
                    """,
                    records,
                    returning=True
                )

                inserted = 0
                while True:
                    inserted += len(cursor.fetchall())
                    if not cursor.nextset():
                        break

                skipped = len(records) - inserted
                print(f"Inserted {inserted} scrobbles, skipped {skipped} duplicates.")

    except psycopg.Error as e:
        print(f"Database error while loading scrobbles: {e}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    load_scrobbles()