#!/bin/bash
set -e

python3 scripts/setup_timezone.py

# Docker Compose reads .env automatically for ${VAR} substitution,
# so DB_TIMEZONE written above is picked up by db's environment block.
docker compose build pipeline
docker compose up -d db