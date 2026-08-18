from extract import fetch_scrobbles
from transform import transform_scrobbles
from validate import validate_scrobbles
from load import load_scrobbles

import pandas as pd
import sys

from config import (
    RAW_DIR,
    PROCESSED_DIR,
    SCROBBLES_CSV,
    VALIDATED_CSV,
    REJECTED_CSV,
)


def run_pipeline():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    print("[1/4] Extracting...")
    fetch_scrobbles()

    print("[2/4] Transforming...")
    transform_scrobbles()

    print("[3/4] Validating...")

    try:
        df = pd.read_csv(SCROBBLES_CSV)
    except FileNotFoundError:
        print(
            f"Input file not found: {SCROBBLES_CSV}",
            file=sys.stderr
        )
        raise SystemExit(1)
    
    valid, rejected = validate_scrobbles(df)

    valid.to_csv(
        VALIDATED_CSV,
        index=False
    )

    rejected.to_csv(
        REJECTED_CSV,
        index=False
    )

    print(f"Rows read: {len(df)}")
    print(f"Valid rows: {len(valid)}")
    print(f"Rejected rows: {len(rejected)}")

    print("[4/4] Loading...")
    load_scrobbles()

    print("\nPipeline completed successfully.")


if __name__ == "__main__":
    run_pipeline()