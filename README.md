# Last.fm Data Pipeline

A small end-to-end ETL pipeline that pulls your listening history (scrobbles) from the Last.fm API, cleans and validates it, and loads it into PostgreSQL — both to preserve your listening history permanently and to enable analytics on top of it.

## Overview

The pipeline runs in four stages:

```
Extract → Transform → Validate → Load
```

1. **Extract** — Pulls recent (or full) scrobble history as raw JSON.
2. **Transform** — Flattens and cleans the raw JSON into a tabular CSV.
3. **Validate** — Checks each row for missing fields or bad timestamps, splitting records into "valid" and "rejected" sets.
4. **Load** — Upserts valid scrobbles into a PostgreSQL database (duplicates are skipped).

Each run is incremental by default: it picks up from the last scrobble timestamp already in the database, so you can schedule it to run repeatedly and build a permanent, ever-growing archive of your listening history without re-processing what's already stored.

## Tech Stack

| **Technology**    | **Role / Use Case**                                   |
| ----------------- | ----------------------------------------------------- |
| **Python**        | Extraction, transformation, validation, orchestration |
| **SQL**           | Querying and database operations                      |
| **PostgreSQL**    | Relational database and data storage                  |
| **Pandas**        | Data transformation                                   |
| **Last.fm API**   | Data source                                           |
| **pytest**        | Testing                                               |
| **python-dotenv** | Configuration and secrets                             |
| **Git**           | Version control                                       |



## Project Structure

```text
src/
├── auth.py         # One-time OAuth-style flow to get a Last.fm session key
├── config.py        # Paths, directories, and logging setup
├── lastfm.py         # Request signing (API signature helper)
├── extract.py        # Pulls scrobbles from the Last.fm API → raw JSON
├── transform.py       # Raw JSON → cleaned CSV
├── validate.py        # Cleaned CSV → valid / rejected CSVs
├── load.py           # Valid CSV → PostgreSQL (upsert, dedup)
└── pipeline.py        # Orchestrates all stages end-to-end

sql/
└── schema.sql        # 'scrobbles' table definition

data/
├── raw/            # Raw API responses (JSON)
├── processed/       # Transformed & validated CSVs
├── quarantine/       # Rejected rows with reasons
└── logs/           # Pipeline run logs

tests/
├── test_lastfm.py      # Request-signing tests
└── test_validate.py     # Validation logic tests
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt   # for running tests
```

### 2. Create your database

Create a PostgreSQL database and apply the schema:

```bash
createdb lastfm
psql -d lastfm -f sql/schema.sql
```

### 3. Create a Last.fm API account

Go to the [Last.fm API account page](https://www.last.fm/api/account/create), log in to your Last.fm account, and create an API account to obtain your **API key** and **API secret**.

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
# Last.fm API credentials
LASTFM_API_KEY=your_api_key
LASTFM_API_SECRET=your_api_secret
LASTFM_USERNAME=your_lastfm_username

# Filled in automatically after running the auth flow
LASTFM_SESSION_KEY=

# PostgreSQL connection
DB_HOST=localhost
DB_PORT=5432
DB_NAME=lastfm
DB_USER=your_user
DB_PASSWORD=your_password
```

### 5. Authenticate with Last.fm

Run the one-time authentication flow to obtain a session key. The session key will be saved automatically to .env:

```bash
python -m src.auth
```

The command will print a URL. Open the URL in your browser, authorize the application, then return to the terminal and press Enter to complete the authentication flow.

## Usage

Run the full pipeline to fetch new scrobbles since the latest scrobble stored in the database:

```bash
python -m src.pipeline
```

Fetch and store your entire listening history:

```bash
python -m src.pipeline --full-history
```

You can also run each pipeline stage independently:

```bash
python -m src.extract    
python -m src.transform  
python -m src.validate   
python -m src.load       
```

## Data Quality

The `validate` stage checks every row for:

- Missing artist or track
- Invalid or unparseable timestamps
- Future timestamps

Rows that fail validation are written to
`data/quarantine/rejected_scrobbles.csv` with a `rejection_reason` column.
Valid rows proceed to the load stage.

## Testing

Run the test suite with verbose output:

```bash
pytest -v
```

The `-v` flag displays each test individually with its result.

The test suite covers request signing (`test_lastfm.py`) and data validation (`test_validate.py`).


## Status

🚧 **Work in progress** — the core ETL flow (extract → transform → validate → load) is functional.

Planned next steps:

- [ ] Additional test coverage for extract, transform, and load
- [ ] SQL queries / views for analytics (top artists, tracks, listening trends)
- [ ] Scheduling (cron / Airflow) for automated incremental runs
