# Last.fm Data Pipeline

A small end-to-end data engineering pipeline that extracts listening history (scrobbles) from the Last.fm API, transforms and validates the data, and loads the data into PostgreSQL.

**[View the live dashboard](https://piotr-machocki.github.io/lastfm-data-pipeline/)**

The project supports three deployment environments:

* **Local PostgreSQL** - PostgreSQL runs directly on the host machine.

* **Docker** - PostgreSQL and the pipeline run through Docker Compose.

* **Google Cloud Platform** - PostgreSQL runs on a GCP VM and the production pipeline is executed by GitHub Actions.

The GCP deployment uses Workload Identity Federation (WIF) for GitHub Actions authentication and Identity-Aware Proxy (IAP) for secure VM access to PostgreSQL.

The pipeline is designed for incremental ingestion, idempotent loading, data quality, persistent storage, SQL-based analytics, and automated dashboard deployment.

## Overview

The pipeline runs in four stages:

```text
Extract → Transform → Validate → Load
```

1. **Extract** - Pulls recent or full scrobble history from the Last.fm API and saves the raw response as JSON.

2. **Transform** - Flattens and cleans the raw JSON into a tabular CSV.

3. **Validate** - Checks each row for missing fields or invalid timestamps, splitting records into valid and rejected sets.

4. **Load** - Loads valid scrobbles into PostgreSQL and skips duplicates.

By default, the pipeline runs incrementally. It checks the latest timestamp already stored in PostgreSQL and requests newer scrobbles from Last.fm.

The pipeline also supports explicit full-history ingestion with:

```bash
python -m src.pipeline --full-history
```

## Architecture

### Local PostgreSQL / Docker

The ETL pipeline is the same in both environments. The difference is where PostgreSQL runs:

* **Local PostgreSQL:** PostgreSQL runs directly on the host machine.

* **Docker:** PostgreSQL runs in the Docker Compose `db` container.

```text
Last.fm API

     ↓

Python ETL

     ↓

PostgreSQL

     ↓

SQL analytics views
```

### GCP / GitHub Actions

```text
                    Last.fm API
                         ↑
                         │
                    API request
                         │
                  GitHub Actions
                         │
                  OpenID Connect
                         ↓
              Workload Identity Federation
                         │
                         ↓
                        IAP
                         │
                         ↓
                      GCP VM
                         │
                         ↓
                    PostgreSQL
```

The GitHub Actions Ubuntu runner retrieves scrobble data from the Last.fm API and loads the processed data into PostgreSQL running on the GCP VM, which serves as the pipeline's persistent data store.

GitHub Actions does not use a Google Cloud service-account key. Authentication is performed using GitHub's OIDC token and Google Cloud Workload Identity Federation.

The PostgreSQL connection is established through an IAP tunnel, so the GCP VM does not require a public external IPv4 address.

## Tech Stack

| Technology                              | Role / Use Case                                       |
| --------------------------------------- | ----------------------------------------------------- |
| **Python**                              | Extraction, transformation, validation, orchestration |
| **SQL**                                 | Database schema and analytics                         |
| **PostgreSQL**                          | Relational database and persistent storage            |
| **Docker**                              | Containerization and reproducible runtime             |
| **Docker Compose**                      | Local multi-container environment                     |
| **Pandas**                              | Data transformation                                   |
| **Last.fm API**                         | Data source                                           |
| **GitHub Actions**                      | Cloud pipeline execution and automation               |
| **Google Cloud Platform**               | Cloud infrastructure                                  |
| **Google Cloud IAP**                    | Secure access to the PostgreSQL VM                    |
| **Google Workload Identity Federation** | Keyless GitHub → GCP authentication                   |
| **pytest**                              | Testing                                               |
| **python-dotenv**                       | Local configuration                                   |
| **Git**                                 | Version control                                       |

## Project Structure

```text
.
├── .github/
│   └── workflows/
│       ├── test-gcp-auth.yml       # Tests GitHub → GCP authentication
│       ├── test-gcp-vm.yml         # Tests VM access through IAP
│       ├── test-postgres.yml       # Tests PostgreSQL connectivity
│       ├── run-pipeline.yml        # Runs the production ETL pipeline
│       └── prepare-pages-data.yml  # Generates dashboard data and deploys GitHub Pages
├── Dockerfile                      # Pipeline container definition
├── docker-entrypoint.py            # Fixes data ownership, then drops privileges
├── docker-compose.yml              # Local PostgreSQL + pipeline services
├── .dockerignore                   # Files excluded from Docker build context
├── requirements.in                 # Direct Python dependencies
├── requirements.txt                # Pinned dependency lockfile
├── requirements-dev.txt            # Development and testing dependencies
├── pyproject.toml                  # pytest configuration
├── src/
│   ├── auth.py                     # Last.fm user authentication flow
│   ├── config.py                   # Paths, directories, and logging configuration
│   ├── lastfm.py                   # Last.fm request-signing helper
│   ├── extract.py                  # Last.fm API → raw JSON
│   ├── transform.py                # Raw JSON → cleaned CSV
│   ├── validate.py                 # Cleaned CSV → valid / rejected CSVs
│   ├── load.py                     # Valid CSV → PostgreSQL
│   └── pipeline.py                 # Orchestrates all stages
├── sql/
│   ├── 01-timezone.sh              # Database timezone configuration
│   ├── 02-schema.sql               # scrobbles table definition
│   └── views.sql                   # Analytics views
├── scripts/
│   ├── local-setup.sh              # Sets up native/local PostgreSQL
│   ├── local-docker-setup.sh       # Sets up Docker PostgreSQL
│   ├── gcp-setup.sh                # Initializes an existing PostgreSQL database on the GCP VM
│   └── setup_timezone.py           # Detects/selects timezone and saves it to .env
├── data/
│   ├── raw/                        # Raw API responses
│   ├── processed/                  # Transformed & validated CSVs
│   ├── quarantine/                 # Rejected rows with reasons
│   └── logs/                       # Pipeline run logs
└── tests/
    ├── test_lastfm.py              # Request-signing tests
    ├── test_validate.py            # Validation tests
    ├── test_transform.py           # Transformation tests
    ├── test_extract.py             # Extraction tests
    └── test_load.py                # Loading tests
```

## Production Last.fm account

The production GitHub Actions workflow currently uses the public Last.fm account `bbcradio1`, which Last.fm identifies as the account used by BBC Radio 1 for scrobbling.

BBC Radio 1 was chosen as the production data source because its Last.fm account continuously receives real-world scrobbles from the radio station. This provides a steady stream of new data for testing incremental ingestion and scheduled pipeline execution.

Using an existing public radio account also avoids creating a dedicated demo Last.fm account and artificially generating synthetic scrobbles just to test the pipeline. The pipeline therefore works with naturally occurring, continuously updated listening data rather than simulated records.

The production workflow uses:

```text
LASTFM_USERNAME=bbcradio1
```

If you want to use your personal listening history instead, replace `bbcradio1` with your own Last.fm username.

## Cloud Cost Design (GCP Always Free)

The cloud environment is designed to remain within the Google Cloud Always Free usage limits under the expected workload.

Last verified against Google's Free Tier documentation: September 2026.

The configuration uses an `e2-micro` VM in `us-central1`, a 10 GB standard persistent disk, and no external IPv4 address.

> Free Tier limits are subject to Google's current pricing terms and can change. Usage above the applicable monthly limits may incur charges.

### Why IAP and no public IPv4

The VM does not use a public external IPv4 address.

Google currently provides only 1 hour/month of free usage for external IPv4 addresses attached to standard VM instances; usage beyond that is billable.

Instead of keeping a public IPv4 address attached to the VM, access is provided through Identity-Aware Proxy (IAP) TCP forwarding.

This provides several benefits:

* No permanent public IPv4 address

* PostgreSQL is not exposed directly through a public IP address

* GitHub Actions does not require a stored Google Cloud service-account key

* Access is controlled through Google Cloud IAM and IAP

### VM specification

| Setting                | Value                            |
| ---------------------- | -------------------------------- |
| Machine type           | `e2-micro`                       |
| Region / zone          | `us-central1 / us-central1-a`    |
| Boot disk              | `pd-standard`, 10 GB             |
| Always Free disk limit | 30 GB standard persistent disk   |
| OS                     | Debian GNU/Linux 13              |
| PostgreSQL             | PostgreSQL 17                    |
| External IP            | None                             |
| Internal IP            | `10.128.0.2`                     |
| Swap                   | 2 GB `/swapfile`                 |
| PostgreSQL tuning      | Default PostgreSQL configuration |

The VM uses a 10 GB standard persistent disk, which is below Google's current 30 GB Always Free allowance.

No custom PostgreSQL memory tuning has been applied. The VM uses the PostgreSQL defaults rather than adding additional configuration for the small `e2-micro` instance.

### Outbound traffic and the 1 GB limit

Google's current Compute Engine Always Free allowance includes up to 1 GB of outbound data transfer per month.

The expected workload is designed to keep network traffic small:

* Normal incremental pipeline runs process only newly available Last.fm scrobbles.

* The pipeline does not download the complete historical dataset on every run.

* Analytics views automatically reflect new data because they query the current contents of the `scrobbles` table.

* The initial full-history ingestion is a separate operation from normal incremental execution.

The 1 GB limit should not be treated as an unlimited allowance. Actual usage should be monitored rather than assumed to be zero.

Large queries that transfer substantial amounts of PostgreSQL data out of the VM could contribute to outbound traffic. Routine incremental ETL runs are expected to transfer much less data.

### Package and OS updates

The VM normally operates without a public external IPv4 address.

During the initial setup, an external IPv4 address was temporarily enabled so that the VM could reach Debian package repositories and install required software.

After the required packages were installed, the external IPv4 address was removed again.

The current VM therefore returns to the no-public-IP configuration after setup.

Temporary IPv4 usage should be treated as a setup operation rather than part of the normal production architecture. Google's current pricing documentation provides only 1 free hour/month of external IPv4 usage for standard VM instances, so future temporary enablement should be kept as short as practical.

For future maintenance, package updates can similarly be performed during a short controlled maintenance window, followed by removal of the external IPv4 address.

### Cost monitoring

The GCP project uses an automated cost-protection mechanism in addition to normal billing monitoring.

A billing budget is configured for the `lastfm-data-platform` project with a threshold of approximately **2 PLN per month**. When the configured billing threshold is reached, Google Cloud publishes a budget notification through **Pub/Sub**.

A Node.js-based serverless function processes the notification and disables billing for the project. This provides an additional safety mechanism intended to prevent an unexpected increase in cloud charges from continuing indefinitely.

The mechanism is separate from the data pipeline itself:

```text
GCP Billing

     │

     ↓

Billing Budget

     │

     │ threshold reached

     ↓

Pub/Sub

     │

     ↓

Node.js billing-protection function

     │

     ↓

Disable billing

     │

     ↓

lastfm-data-platform
```

The cost-protection mechanism is intended as a **safety net**, not as a guarantee that the project can never exceed 2 PLN. Cloud billing data and budget notifications are not necessarily instantaneous, so actual charges can exceed the configured threshold before the billing shutdown takes effect.

The function and its configuration are maintained separately from the ETL pipeline code because they operate at the GCP project/billing level rather than being part of the pipeline execution path.

## Last.fm Data Access

The pipeline retrieves scrobble history using the Last.fm API.

The required Last.fm configuration depends on whether the requested history is accessible through the public API or requires an authenticated Last.fm session.

### Public scrobble history

For a Last.fm profile whose recent tracks are accessible through the public API, the pipeline needs:

```env
LASTFM_API_KEY=your_api_key
LASTFM_USERNAME=your_lastfm_username
```

The `user.getrecenttracks` endpoint used by this pipeline can be called without a user session when the requested history is available through the public API.

A Last.fm API shared secret and `auth.py` are therefore not required for the normal public-history case.

To obtain an API key, log in to your Last.fm account and [create a Last.fm API account](https://www.last.fm/api/account/create).

### Private scrobble history

Last.fm profiles can have recent tracks set to private.

If an unauthenticated `user.getrecenttracks` request cannot access the required history, the application can use Last.fm's user-authentication flow to obtain an authenticated session.

This requires:

* Last.fm API key

* Last.fm API shared secret

* Last.fm user authorization

* A session key generated by the authentication flow

The authentication flow is implemented in:

```text
src/auth.py
```

The resulting session key can be stored in `.env`:

```env
LASTFM_API_KEY=your_api_key
LASTFM_API_SECRET=your_api_secret
LASTFM_USERNAME=your_lastfm_username
LASTFM_SESSION_KEY=your_session_key
```

The authenticated session is used when the pipeline needs authenticated Last.fm API access.

### Which configuration do I need?

| Last.fm history                        | API key  | Username | Shared secret | Session key  |
| -------------------------------------- | -------- | -------- | ------------- | ------------ |
| Public / accessible through public API | Required | Required | Not required  | Not required |
| Requires authenticated access          | Required | Required | Required      | Required     |

## Choose Your Setup

There are three supported ways to run the project.

### Local PostgreSQL

Use this setup when PostgreSQL is installed directly on your machine.

```bash
./scripts/local-setup.sh
```

The Python pipeline is then run directly from the host environment:

```bash
python -m src.pipeline
```

### Docker

Use this setup when you want PostgreSQL and the pipeline environment managed by Docker Compose.

```bash
./scripts/local-docker-setup.sh
```

The pipeline is then run through Docker Compose:

```bash
docker compose run --rm pipeline
```

### GCP + GitHub Actions

Use this setup for the production-style cloud deployment.

PostgreSQL runs on a GCP VM and the ETL pipeline is executed by GitHub Actions. GitHub Actions authenticates to Google Cloud using Workload Identity Federation and connects to PostgreSQL through an IAP tunnel.

This setup additionally requires:

* Running GCP VM instance

* Configured Postgres on the VM

* GitHub Actions secrets

## Local PostgreSQL

Use this setup when PostgreSQL is installed directly on the host machine.

### Requirements

* Python 3.14+

* PostgreSQL

* Last.fm API key

If authenticated Last.fm access is required, also configure the Last.fm shared secret and session key as described in [Last.fm Data Access](#lastfm-data-access).

### Local `.env`

For local development, create a `.env` file in the project root:

```env
# Last.fm API

LASTFM_API_KEY=your_api_key

LASTFM_API_SECRET=your_api_secret

LASTFM_USERNAME=your_lastfm_username

# Optional: only required when using authenticated Last.fm access

LASTFM_SESSION_KEY=

# Filled in by scripts/setup_timezone.py

DB_TIMEZONE=

# PostgreSQL

DB_NAME=lastfm

DB_USER=your_user

DB_PASSWORD=your_password

DB_HOST=localhost

DB_PORT=5432
```

The `.env` file is local configuration and must not be committed to Git.

### Setup

Run:

```bash
./scripts/local-setup.sh
```

The script:

1. Detects or asks for the database timezone.

2. Saves `DB_TIMEZONE` to `.env`.

3. Creates the local database if necessary.

4. Applies the PostgreSQL schema.

5. Configures the database timezone.

6. Applies the analytics views.

### Run the pipeline

Incremental run:

```bash
python -m src.pipeline
```

Full-history run:

```bash
python -m src.pipeline --full-history
```

## Docker

Use this setup when PostgreSQL and the pipeline are managed by Docker Compose.

Docker requires Docker Desktop on macOS/Windows or Docker Engine with Docker Compose on Linux.

### Setup

Run:

```bash
./scripts/local-docker-setup.sh
```

The setup script:

1. Detects or asks for the database timezone.

2. Saves `DB_TIMEZONE` to `.env`.

3. Builds the pipeline image.

4. Starts PostgreSQL.

5. Waits for PostgreSQL to become healthy.

6. Initializes the database schema and analytics views.

The pipeline itself is not executed during setup.

### Incremental run

```bash
docker compose run --rm pipeline
```

### Full-history run

```bash
docker compose run --rm pipeline python -m src.pipeline --full-history
```

### Check the database

View the total number of scrobbles:

```bash
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT COUNT(*) FROM scrobbles;"'
```

Show the 50 most recent scrobbles:

```bash
docker compose exec db sh -c 'psql -P pager=off -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT artist, track, album, timestamp FROM scrobbles ORDER BY timestamp DESC LIMIT 50;"'
```

### Stop the services

```bash
docker compose down
```

This removes the containers and network but preserves the PostgreSQL data volume.

The local `./data` directory is mounted into the pipeline container, so generated JSON, CSV, quarantine, and log files remain on the host.

### Local PostgreSQL vs Docker

The ETL pipeline and database schema are the same in both environments. The main difference is where PostgreSQL and the Python runtime are executed.

|                 | Local PostgreSQL        | Docker                  |
| --------------- | ----------------------- | ----------------------- |
| PostgreSQL      | Host machine            | Docker container        |
| Pipeline        | Host Python environment | Pipeline container      |
| Setup script    | `local-setup.sh`        | `local-docker-setup.sh` |
| Configuration   | `.env`                  | `.env` + Docker Compose |
| Database schema | Same                    | Same                    |
| Analytics views | Same                    | Same                    |

## Google Cloud

The production-style environment uses PostgreSQL running on a GCP VM.

The PostgreSQL database and PostgreSQL user are provisioned separately on the GCP VM. The `gcp-setup.sh` script initializes the existing PostgreSQL database rather than creating the database or user.

### GCP architecture

The PostgreSQL database on the GCP VM is accessed through an IAP tunnel.

The VM does not require a public external IPv4 address.

The architecture is:

```text
GitHub Actions

      │

      │ OIDC / Workload Identity Federation

      ↓

Google Cloud

      │

      │ IAP TCP tunnel

      ↓

GCP VM

      │

      ↓

PostgreSQL
```

### GCP database setup

Start the tunnel locally:

```bash
gcloud compute start-iap-tunnel lastfm-server 5432 \
  --local-host-port=127.0.0.1:5433 \
  --zone=us-central1-a
```

Configure `.env` for the PostgreSQL database on the GCP VM:

```env
DB_HOST=127.0.0.1
DB_PORT=5433
DB_NAME=lastfm_professional
DB_USER=lastfm_professional_user
DB_PASSWORD=your_password
```

Then run:

```bash
./scripts/gcp-setup.sh
```

The script:

1. Detects or asks for the database timezone.

2. Tests the PostgreSQL connection.

3. Applies `sql/02-schema.sql`.

4. Configures the database timezone.

5. Applies `sql/views.sql`.

The script does not create the GCP VM, install PostgreSQL, create the PostgreSQL database, or create the PostgreSQL role. Those resources are provisioned separately.

### Verify the database

Check the tables:

```bash
psql \
  -h 127.0.0.1 \
  -p 5433 \
  -U lastfm_professional_user \
  -d lastfm_professional \
  -c "\dt"
```

Check the analytics views:

```bash
psql \
  -h 127.0.0.1 \
  -p 5433 \
  -U lastfm_professional_user \
  -d lastfm_professional \
  -c "\dv"
```

### Network and access

PostgreSQL listens on the VM's internal VPC address:

```text
10.128.0.2
```

IAP TCP forwarding uses the source range:

```text
35.235.240.0/20
```

The current GCP VPC firewall contains the following PostgreSQL-specific ingress rule:

```text
Rule:          allow-iap-postgresql
Direction:     INGRESS
Source range:  35.235.240.0/20
Protocol:      TCP
Port:          5432
```

The firewall therefore permits TCP connections to PostgreSQL on port `5432` from the IAP forwarding range.

Google's documentation specifies this range for IAP TCP forwarding and recommends allowing only the ports required by the VM.

### PostgreSQL access

The production database is:

```text
Database: lastfm_professional
User: lastfm_professional_user
```

PostgreSQL access is provided through the IAP tunnel rather than through a public PostgreSQL endpoint.

The relevant `pg_hba.conf` rules currently restrict the application database users to the IAP source range and require SCRAM-SHA-256 authentication:

```text
host    lastfm_personal       lastfm_personal_user       35.235.240.0/20       scram-sha-256

host    lastfm_professional   lastfm_professional_user   35.235.240.0/20       scram-sha-256
```

The security chain is therefore:

```text
IAP TCP forwarding

       ↓

35.235.240.0/20

       ↓

GCP firewall: TCP 5432

       ↓

10.128.0.2:5432

       ↓

PostgreSQL pg_hba.conf

       ↓

SCRAM-SHA-256 authentication

       ↓

PostgreSQL database
```

## GitHub Actions

The production pipeline is executed by GitHub Actions.

Unlike the local and Docker setups, the GitHub Actions environment does not use the repository's local `.env` file for production secrets.

The workflow uses GitHub repository secrets and workflow environment variables.

### Authentication

The production pipeline workflow:

1. Checks out the repository.

2. Sets up Python 3.14.

3. Authenticates to Google Cloud using GitHub OIDC.

4. Uses Google Cloud Workload Identity Federation to impersonate the GitHub Actions service account.

5. Starts an IAP tunnel to the PostgreSQL server.

6. Installs the required dependencies.

7. Runs the ETL pipeline against the PostgreSQL database running on the GCP VM.

The Google Cloud service account does not require a stored private key. Authentication is handled through Workload Identity Federation.

### Automated execution

The production ETL pipeline runs automatically every 12 hours:

* **00:00 UTC**
* **12:00 UTC**

The pipeline workflow can also be started manually through GitHub Actions.

A separate Pages workflow runs automatically once per day:

* **14:00 UTC**

The Pages workflow queries the PostgreSQL analytics views, generates JSON datasets, and deploys the dashboard to GitHub Pages.

The Pages workflow can also be started manually through GitHub Actions.

### Required GitHub Secrets

The workflow requires:

```text
LASTFM_API_KEY

PROFESSIONAL_DB_PASSWORD
```

The production workflow currently uses the public `bbcradio1` Last.fm account, so it does not require a Last.fm session key.

The GitHub Actions workflow therefore does not need `LASTFM_API_SECRET` or `LASTFM_SESSION_KEY` for the current production data source.

### Manual workflow execution

The pipeline can currently be started manually from:

```text
GitHub → Actions → Run Last.fm Pipeline → Run workflow
```

The Pages deployment can be started manually from:

```text
GitHub → Actions → Prepare Pages Data → Run workflow
```

The pipeline uses the `lastfm_professional` PostgreSQL database running on the GCP VM and connects to it through an IAP tunnel.

## Incremental Ingestion

Incremental ingestion is the default behavior.

Before extraction, the pipeline checks the latest timestamp already stored:

```sql
SELECT MAX(timestamp)
FROM scrobbles;
```

If previous data exists, this timestamp is used as the incremental cursor.

The PostgreSQL load is idempotent and uses the following uniqueness constraint:

```text
artist + track + timestamp
```

Duplicate records are therefore skipped instead of inserted again.

> **Note:** `--full-history` controls the pipeline's extraction behavior. It does not depend on whether PostgreSQL is running locally, in Docker, or on GCP.

## Full-history Ingestion

A full-history run can be explicitly requested:

```bash
python -m src.pipeline --full-history
```

Docker:

```bash
docker compose run --rm pipeline python -m src.pipeline --full-history
```

Full-history ingestion is intended for initial population or rebuilding an archive. Regular runs should use the default incremental mode.

## Data Quality

The `validate` stage checks every row for:

* Missing artist

* Missing track

* Invalid or unparseable timestamps

* Future timestamps

Rows that fail validation are written to:

```text
data/quarantine/rejected_scrobbles.csv
```

The file contains a `rejection_reason` column describing why each row was rejected.

Only valid rows proceed to the load stage.

> **Note:** The quarantine file is written to the pipeline's local `data/` directory. It persists on the host when running locally or with Docker (where `./data` is mounted into the container). In the GitHub Actions production workflow, the runner is ephemeral and the file is discarded when the job finishes; only the rejected-row count remains visible in that run's logs.

## Analytics

The PostgreSQL database contains SQL views for common listening-history analysis:

* `overview`

* `top_artists`

* `top_tracks`

* `hourly_listening_pattern`

* `monthly_summary`

* `yearly_summary`

Example:

```sql
SELECT *
FROM top_artists
LIMIT 10;
```

These views operate directly on the PostgreSQL `scrobbles` table and provide the datasets used by the dashboard.

## Dashboard

The project includes a static dashboard published through GitHub Pages.

**[View the live dashboard](https://piotr-machocki.github.io/lastfm-data-pipeline/)**

The dashboard currently displays:

* Total scrobbles
* Unique artists
* Most played artist
* Most played track
* Top artists
* Top tracks
* Yearly listening
* Monthly listening
* Listening by hour

The dashboard is built with HTML, CSS, JavaScript, and Chart.js.

The dashboard data is generated automatically from the PostgreSQL analytics views. The Pages workflow creates the JSON datasets on the GitHub Actions runner and includes them in the GitHub Pages deployment.

Generated JSON files are not committed to the repository.

## Testing

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run the test suite:

```bash
pytest -v
```

The test suite covers request signing, extraction, transformation, validation, and loading.

## Status

### Implemented

* Last.fm API integration

* Incremental ingestion

* Full-history ingestion

* Data transformation

* Data validation

* Idempotent PostgreSQL loading

* PostgreSQL persistence

* PostgreSQL timezone configuration

* Automatic/manual timezone selection

* Docker Compose development environment

* Local PostgreSQL setup

* GCP PostgreSQL setup

* Google Cloud IAP access

* GitHub Actions pipeline execution

* Scheduled GitHub Actions pipeline runs

* GitHub OIDC authentication

* Google Cloud Workload Identity Federation

* Database health/connectivity checks

* Structured logging

* Automated tests

* Pinned dependencies

* SQL analytics views

* Automated dashboard data generation

* GitHub Pages dashboard

* Chart.js data visualization

* Scheduled daily dashboard deployment

### Planned

* Initial full-history ingestion of the complete production dataset

* Additional analytics and reporting

* Further cloud infrastructure improvements

## License

This project is licensed under the [MIT License](LICENSE).
