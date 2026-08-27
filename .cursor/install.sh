#!/usr/bin/env bash
#
# Idempotent environment bootstrap for the django-cards example project.
# Installs system + Python dependencies, initialises a local PostgreSQL
# cluster, and seeds the example database. Safe to run repeatedly.
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PGDATA="${PGDATA:-$HOME/pgdata}"
VENV="$REPO_ROOT/.venv"
export PATH="$HOME/.local/bin:$PATH"

echo "==> Installing system packages"
if ! command -v pg_ctl >/dev/null 2>&1 && ! ls /usr/lib/postgresql/*/bin/pg_ctl >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq postgresql postgresql-contrib build-essential libpq-dev curl git
fi

PGBIN="$(ls -d /usr/lib/postgresql/*/bin | sort -V | tail -1)"

echo "==> Installing uv + Python 3.11"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
uv python install 3.11

echo "==> Creating virtualenv and installing requirements"
if [ ! -x "$VENV/bin/python" ]; then
  uv venv --python 3.11 "$VENV"
fi
uv pip install --python "$VENV/bin/python" -r "$REPO_ROOT/requirements.txt"

echo "==> Initialising PostgreSQL cluster"
if [ ! -f "$PGDATA/PG_VERSION" ]; then
  "$PGBIN/initdb" -D "$PGDATA" -U postgres --auth=trust >/dev/null
fi

echo "==> Starting PostgreSQL (temporary, for DB setup)"
if ! "$PGBIN/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1; then
  "$PGBIN/pg_ctl" -D "$PGDATA" -l "$HOME/pg.log" -o "-p 5432 -k /tmp" -w start
fi

echo "==> Ensuring role + database exist"
"$PGBIN/psql" -h /tmp -p 5432 -U postgres -tc \
  "SELECT 1 FROM pg_roles WHERE rolname='django_cards'" | grep -q 1 || \
  "$PGBIN/psql" -h /tmp -p 5432 -U postgres -c \
  "CREATE USER django_cards WITH PASSWORD 'django_cards' CREATEDB SUPERUSER;"
"$PGBIN/psql" -h /tmp -p 5432 -U postgres -tc \
  "SELECT 1 FROM pg_database WHERE datname='django_cards'" | grep -q 1 || \
  "$PGBIN/psql" -h /tmp -p 5432 -U postgres -c \
  "CREATE DATABASE django_cards OWNER django_cards;"

# The example settings connect to host "db_cards" (a docker-compose service
# name). Map it to localhost so the app can reach the local cluster.
grep -q "db_cards" /etc/hosts || echo "127.0.0.1 db_cards" | sudo tee -a /etc/hosts >/dev/null

echo "==> Applying migrations and seeding example data"
(
  cd "$REPO_ROOT/django_examples"
  export PYTHONPATH="$REPO_ROOT"
  "$VENV/bin/python" manage.py migrate --noinput
  "$VENV/bin/python" manage.py import_cards
)

echo "==> Stopping temporary PostgreSQL (start.sh runs it per-boot)"
"$PGBIN/pg_ctl" -D "$PGDATA" -w stop >/dev/null 2>&1 || true

echo "==> install.sh complete"
