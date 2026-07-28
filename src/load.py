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
    # Data prep happens OUTSIDE the DB try/except: a bad CSV path, a
    # malformed CSV, or a missing column is a programming/data bug, not
    # a database error, and should fail loud with its real traceback.
    df = pd.read_csv(CSV_PATH)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"scrobbles.csv is missing required columns: {missing}")

    records = list(
        df[["artist", "track", "album", "timestamp"]].itertuples(index=False, name=None)
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

                # executemany batches all rows in one round trip instead of
                # one execute() per row - much faster for anything but tiny
                # CSVs, and psycopg3 pipelines it efficiently under the hood.
                cursor.executemany(
                    """
                    INSERT INTO scrobbles (artist, track, album, timestamp)
                    VALUES (%s, %s, %s, %s);
                    """,
                    records,
                )
        # psycopg's connection context manager commits on clean exit
        # (already reached here) and rolls back automatically if an
        # exception propagates out of the `with` block above.

    except psycopg.Error as e:
        # Genuine database problems: connection refused, bad credentials,
        # constraint violation, syntax error in SQL, serialization failure,
        # etc. These are expected-ish failure modes worth a clean message.
        print(f"Database error while loading scrobbles: {e}", file=sys.stderr)
        raise SystemExit(1)

    print(f"Loaded {len(records)} scrobbles successfully!")


if __name__ == "__main__":
    load_scrobbles()