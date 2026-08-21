from src.extract import fetch_scrobbles
from src.transform import transform_scrobbles
from src.validate import validate_scrobbles
from src.load import load_scrobbles

import logging
import pandas as pd

from src.config import (
    RAW_DIR,
    PROCESSED_DIR,
    SCROBBLES_CSV,
    VALIDATED_CSV,
    REJECTED_CSV,
    setup_logging,
)

logger = logging.getLogger(__name__)


def run_pipeline():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("[1/4] Extracting...")
    fetch_scrobbles()

    logger.info("[2/4] Transforming...")
    transform_scrobbles()

    logger.info("[3/4] Validating...")

    try:
        df = pd.read_csv(SCROBBLES_CSV)
    except FileNotFoundError:
        logger.error("Input file not found: %s", SCROBBLES_CSV)
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

    logger.info("Rows read: %d", len(df))
    logger.info("Valid rows: %d", len(valid))
    logger.info("Rejected rows: %d", len(rejected))

    logger.info("[4/4] Loading...")
    load_scrobbles()

    logger.info("Pipeline completed successfully.")


if __name__ == "__main__":
    setup_logging()
    run_pipeline()