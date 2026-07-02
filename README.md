# Last.fm Data Pipeline

## Overview
This is a simple Data Engineering project that ingests listening data from the Last.fm API, processes it, and loads it into a database for analytics.

## Goal
To build an end-to-end ETL pipeline and learn core Data Engineering concepts:
- API data extraction
- Data transformation with Python
- Loading data into a database
- Basic analytics with SQL

## Data Source
- Last.fm API (user scrobbles / recent tracks)

## Architecture
Extract → Transform → Load → Analytics

## Tech Stack
- Python
- Last.fm API
- PostgreSQL
- pandas

## Project Structure

```text
src/
├── extract.py      # Extract data from Last.fm API
├── transform.py    # Clean and transform data
└── load.py         # Load data into PostgreSQL

data/
├── raw/            # Raw API responses
└── processed/      # Cleaned datasets
```

## Features (WIP)
- Extract listening history from Last.fm
- Clean and normalize data
- Store in PostgreSQL
- Run SQL queries for insights (top artists, tracks, listening trends)

## Status
🚧 In progress (first version)
