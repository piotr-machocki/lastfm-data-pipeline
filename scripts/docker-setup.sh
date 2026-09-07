#!/bin/bash
set -e

python3 scripts/setup_timezone.py

# Docker Compose reads .env automatically for ${VAR} substitution,
# so DB_TIMEZONE written above is picked up by db's environment block.
docker compose up --build

# TODO: once sql/views.sql is implemented, apply it here, e.g.:
# docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -f - < sql/views.sql