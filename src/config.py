import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))

RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

SCROBBLES_JSON = RAW_DIR / "scrobbles.json"
SCROBBLES_CSV = PROCESSED_DIR / "scrobbles.csv"
VALIDATED_CSV = PROCESSED_DIR / "validated_scrobbles.csv"
REJECTED_CSV = PROCESSED_DIR / "rejected_scrobbles.csv"