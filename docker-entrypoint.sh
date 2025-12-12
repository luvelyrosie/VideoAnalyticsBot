#!/bin/bash
set -e

echo "Waiting for PostgreSQL to be ready..."
while ! pg_isready -h postgres -U postgres; do
    sleep 1
done

echo "Running database migrations..."
PGPASSWORD=postgres123 psql -h postgres -U postgres -d video_stats -f /app/migrations/01_create_tables.sql

echo "Loading data from JSON..."
python src/load_data.py

echo "Starting Telegram bot..."
exec python src/bot.py