import pandas as pd
import sys
from config import SCROBBLES_CSV, VALIDATED_CSV, REJECTED_CSV

REQUIRED_COLUMNS = {"artist", "track", "album", "timestamp"}

def validate_scrobbles(df):
    missing = REQUIRED_COLUMNS - set(df.columns)

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.reset_index(drop=True)

    rejected = []

    # Check missing artist
    missing_artist = (
        df["artist"].fillna("").astype(str).str.strip().eq("")
    )

    for index in df[missing_artist].index:
        rejected.append((index, "Missing artist"))

    # Check missing track
    missing_track = (
        df["track"].fillna("").astype(str).str.strip().eq("")
    )

    for index in df[missing_track].index:
        rejected.append((index, "Missing track"))

    # Check invalid timestamp
    parsed_timestamp = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
        utc=True
    )
    invalid_timestamp = parsed_timestamp.isna()

    for index in df[invalid_timestamp].index:
        rejected.append((index, "Invalid timestamp"))

    # Check future timestamp
    future_timestamp = parsed_timestamp > pd.Timestamp.now(tz="UTC")

    for index in df[future_timestamp & ~invalid_timestamp].index:
        rejected.append((index, "Future timestamp"))

    # Create rejected dataframe
    rejected_indexes = set(index for index, reason in rejected)

    rejected_df = df.loc[sorted(rejected_indexes)].copy()

    reasons = {}

    for index, reason in rejected:
        if index in reasons:
            reasons[index] += f"; {reason}"
        else:
            reasons[index] = reason

    rejected_df["rejection_reason"] = rejected_df.index.map(reasons)

    # Valid rows = everything not rejected
    valid_df = df.drop(index=rejected_indexes).copy()

    return valid_df, rejected_df


if __name__ == "__main__":
    try:
        df = pd.read_csv(SCROBBLES_CSV)
    except FileNotFoundError:
        print(
            f"Input file not found: {SCROBBLES_CSV}",
            file=sys.stderr
        )
        raise SystemExit(1)

    valid, rejected = validate_scrobbles(df)

    print(f"Rows read: {len(df)}")
    print(f"Valid rows: {len(valid)}")
    print(f"Rejected rows: {len(rejected)}")

    valid.to_csv(
        VALIDATED_CSV,
        index=False
    )

    rejected.to_csv(
        REJECTED_CSV,
        index=False
    )
    