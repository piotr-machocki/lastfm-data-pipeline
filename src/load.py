import os

import pandas as pd
import psycopg
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


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

            df = pd.read_csv("data/processed/scrobbles.csv")

            for _, row in df.iterrows():
                cursor.execute(
                    """
                    INSERT INTO scrobbles (artist, track, album, timestamp)
                    VALUES (%s, %s, %s, %s);
                    """,
                    (
                        row["artist"],
                        row["track"],
                        row["album"],
                        row["timestamp"],
                    )
                )

            print("Data loaded successfully!")

except Exception as e:
    print(f"Error loading data: {e}")