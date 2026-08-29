# Last.fm Data Pipeline

A small end-to-end ETL pipeline that pulls listening history (scrobbles) from the Last.fm API, cleans and validates it, and loads it into PostgreSQL.

The pipeline is containerized with Docker Compose and designed for incremental ingestion, persistent storage, data quality, and analytics.

## Overview

The pipeline runs in four stages:

```text
Extract → Transform → Validate → Load
```

1. **Extract** - Pulls recent or full scrobble history from the Last.fm API and saves the raw response as JSON.

2. **Transform** - Flattens and cleans the raw JSON into a tabular CSV.

3. **Validate** - Checks each row for missing fields or invalid timestamps, splitting records into valid and rejected sets.

4. **Load** - Loads valid scrobbles into PostgreSQL and skips duplicates.

Each run is incremental by default: it starts from the latest scrobble already stored in the database. This allows the pipeline to run repeatedly and build a permanent archive while avoiding duplicate records.

## Tech Stack

| Technology | Role / Use Case |
|---|---|
| **Python** | Extraction, transformation, validation, orchestration |
| **SQL** | Database schema and queries |
| **PostgreSQL** | Relational database and data storage |
| **Docker** | Containerization and reproducible runtime environment |
| **Docker Compose** | Multi-container orchestration |
| **Pandas** | Data transformation and validation |
| **Last.fm API** | Data source |
| **pytest** | Testing |
| **python-dotenv** | Configuration and secrets |
| **Git** | Version control |

## Project Structure

```text
.
├── Dockerfile              # Pipeline container definition
├── docker-compose.yml      # PostgreSQL + pipeline services
├── .dockerignore           # Files excluded from Docker build context
├── requirements.in         # Direct Python dependencies
├── requirements.txt        # Pinned dependency lockfile
├── requirements-dev.txt    # Development and testing dependencies
│
├── src/
│   ├── auth.py             # One-time flow to obtain a Last.fm session key
│   ├── config.py           # Paths, directories, and logging setup
│   ├── lastfm.py           # Last.fm request-signing helper
│   ├── extract.py          # Last.fm API → raw JSON
│   ├── transform.py        # Raw JSON → cleaned CSV
│   ├── validate.py         # Cleaned CSV → valid / rejected CSVs
│   ├── load.py             # Valid CSV → PostgreSQL
│   └── pipeline.py         # Orchestrates all stages
│
├── sql/
│   └── schema.sql          # scrobbles table definition
│
├── data/
│   ├── raw/                # Raw API responses (JSON)
│   ├── processed/          # Transformed & validated CSVs
│   ├── quarantine/         # Rejected rows with reasons
│   └── logs/               # Pipeline run logs
│
└── tests/
    ├── test_lastfm.py      # Request-signing tests
    └── test_validate.py    # Validation logic tests
```

## Setup

Both execution paths require a Last.fm API account and a `.env` file first. Then choose **Docker** or **Manual / local** execution.

### 1. Create a Last.fm API account

Go to the [Last.fm API account page](https://www.last.fm/api/account/create), log in to your Last.fm account, and create an API account to obtain your **API key** and **API secret**.

### 2. Configure environment variables

Create a `.env` file in the project root:

```env
# Last.fm API credentials
LASTFM_API_KEY=your_api_key
LASTFM_API_SECRET=your_api_secret
LASTFM_USERNAME=your_lastfm_username

# Filled in automatically after running the auth flow
LASTFM_SESSION_KEY=

# PostgreSQL connection
DB_NAME=lastfm
DB_USER=your_user
DB_PASSWORD=your_password

# Only needed for manual/local runs - Docker Compose overrides these
DB_HOST=localhost
DB_PORT=5432
```

### 3. Authenticate with Last.fm

Install the project dependencies and run the one-time authentication flow:

```bash
pip install -r requirements.txt
python -m src.auth
```

The command will print a URL. Open the URL in your browser, authorize the application, then return to the terminal and press Enter.

The session key is saved automatically to `.env` as `LASTFM_SESSION_KEY`.

---

## Docker

Requires **Docker Desktop** on macOS/Windows or **Docker Engine + the Docker Compose plugin** on Linux.

On macOS or Windows, install Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop/) and make sure it is running before continuing. Otherwise, `docker compose` commands will fail to connect to the Docker daemon.

### First run

Build the pipeline image and start the services:

```bash
docker compose up --build
```

The PostgreSQL database is initialized automatically, and `sql/schema.sql` is applied when the database volume is created for the first time.

The pipeline waits for PostgreSQL to become healthy before starting.

### Incremental runs

Run the pipeline again to fetch new scrobbles:

```bash
docker compose up
```

### Full history

Fetch and store the entire listening history:

```bash
docker compose run --rm pipeline python -m src.pipeline --full-history
```

### Check the database

`${DB_USER}` below is read from your shell environment, not from `.env` directly. Export it first (or source your `.env` file):

```bash
set -a; source .env; set +a
```

Then:

```bash
docker compose exec db psql -U ${DB_USER} -d lastfm -c "SELECT COUNT(*) FROM scrobbles;"
```

### Stop the services

```bash
docker compose down
```

This removes the containers and network but preserves the PostgreSQL data volume.

The local `./data` directory is mounted into the pipeline container, so generated JSON, CSV, quarantine, and log files remain on the host.

### Run individual stages

Individual stages can also be executed inside the pipeline container:

```bash
docker compose run --rm pipeline python -m src.extract
docker compose run --rm pipeline python -m src.transform
docker compose run --rm pipeline python -m src.validate
docker compose run --rm pipeline python -m src.load
```

---

## Running Locally

**Requirements:** Python 3.14+ and a running PostgreSQL instance.

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create the database

Create a PostgreSQL database and apply the schema:

```bash
createdb lastfm
psql -d lastfm -f sql/schema.sql
```

### 3. Run the pipeline

Run the incremental pipeline:

```bash
python -m src.pipeline
```

Fetch and store the entire listening history:

```bash
python -m src.pipeline --full-history
```

### Run individual stages

```bash
python -m src.extract
python -m src.transform
python -m src.validate
python -m src.load
```

---

## Data Quality

The `validate` stage checks every row for:

- Missing artist or track
- Invalid or unparseable timestamps
- Future timestamps

Rows that fail validation are written to:

```text
data/quarantine/rejected_scrobbles.csv
```

with a `rejection_reason` column.

Valid rows proceed to the load stage.

## Testing

For development and testing, install the dev dependencies:
 
```bash
pip install -r requirements-dev.txt
```

Run the test suite with verbose output:
 
```bash
pytest -v
```
 
The `-v` flag displays each test individually with its result.
 
The test suite covers request signing (`test_lastfm.py`) and data validation (`test_validate.py`).

## Status

🚧 **Work in progress** — the core ETL pipeline is functional and containerized with Docker Compose.

Implemented:

- Incremental ingestion
- Full-history ingestion
- Data validation
- Idempotent loading
- PostgreSQL persistence
- Docker Compose orchestration
- Database health checks
- Structured logging
- Automated tests
- Pinned dependency management

Planned next steps:

- [ ] Additional test coverage for extract, transform, and load
- [ ] SQL queries / views for analytics (top artists, tracks, listening trends)
- [ ] Scheduling (cron / Airflow) for automated incremental runs

## License

This project is licensed under the [MIT License](LICENSE).