#!/usr/bin/env bash
#
# Per-boot startup for the django-cards development environment.
# Brings up PostgreSQL, ensures the app role/database exist, applies
# migrations and seeds example data. Safe to run repeatedly.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# The example settings connect to the host "db_cards" (the docker-compose
# service name). Point it at the local PostgreSQL server.
if ! grep -q 'db_cards' /etc/hosts; then
    echo '127.0.0.1 db_cards' | sudo tee -a /etc/hosts >/dev/null
fi

# Start PostgreSQL (idempotent: no-op if already running).
sudo service postgresql start

# Wait for PostgreSQL to accept connections.
for _ in $(seq 1 30); do
    if sudo -u postgres pg_isready -q; then
        break
    fi
    sleep 1
done

# Ensure the application role and database exist.
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='django_cards'" | grep -q 1; then
    sudo -u postgres psql -c "CREATE USER django_cards WITH PASSWORD 'django_cards' CREATEDB;"
fi
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='django_cards'" | grep -q 1; then
    sudo -u postgres psql -c "CREATE DATABASE django_cards OWNER django_cards;"
fi

# Apply migrations and seed example data on first run.
export PYTHONPATH="$REPO_ROOT"
cd "$REPO_ROOT/django_examples"
"$REPO_ROOT/.venv/bin/python" manage.py migrate --noinput

if [ "$("$REPO_ROOT/.venv/bin/python" manage.py shell -c 'from cards_examples.models import Company; print(Company.objects.count())' 2>/dev/null | tail -1)" = "0" ]; then
    "$REPO_ROOT/.venv/bin/python" manage.py import_cards
fi
