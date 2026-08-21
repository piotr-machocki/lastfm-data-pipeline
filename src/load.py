import os
import logging

import pandas as pd
import psycopg
from dotenv import load_dotenv

from src.config import VALIDATED_CSV

logger = logging.getLogger(__name__)

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
    logger.error("Missing required DB environment variables. Check your .env file.")
    raise SystemExit(1)

REQUIRED_COLUMNS = {"artist", "track", "album", "timestamp"}


def load_scrobbles() -> None:
    logger.info("Loading scrobbles into PostgreSQL")

    try:
        df = pd.read_csv(VALIDATED_CSV)
    except FileNotFoundError:
        logger.error("Input file not found: %s", VALIDATED_CSV)
        raise SystemExit(1)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        logger.error(
            "%s is missing required columns: %s",
            VALIDATED_CSV,
            missing,
        )
        raise SystemExit(1)

    df = df[["artist", "track", "album", "timestamp"]]
    df = df.astype(object).where(df.notna(), None)

    records = list(df.itertuples(index=False, name=None))

    if not records:
        logger.info("No records to insert.")
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
                        timestamp TIMESTAMPTZ NOT NULL,
                        UNIQUE (artist, track, timestamp)
                    );
                """)

                inserted = 0

                for record in records:
                    cursor.execute(
                        """
                        INSERT INTO scrobbles (artist, track, album, timestamp)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (artist, track, timestamp) DO NOTHING
                        """,
                        record,
                    )

                    inserted += cursor.rowcount

                skipped = len(records) - inserted
                logger.info(
                    "Inserted %d scrobbles, skipped %d duplicates.",
                    inserted,
                    skipped,
                )

    except psycopg.Error:
        logger.exception("Database error while loading scrobbles")
        raise SystemExit(1)


if __name__ == "__main__":
    from config import setup_logging

    setup_logging()
    load_scrobbles()