import pandas as pd


CSV_PATH = "data/processed/scrobbles.csv"
REJECTED_PATH = "data/processed/rejected_scrobbles.csv"


def validate_scrobbles(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split scrobbles into valid and rejected records.
    """

    valid = df.copy()
    rejected = pd.DataFrame()

    return valid, rejected


if __name__ == "__main__":
    
    df = pd.read_csv(CSV_PATH)

    valid, rejected = validate_scrobbles(df)

    print(f"Valid rows: {len(valid)}")
    print(f"Rejected rows: {len(rejected)}")