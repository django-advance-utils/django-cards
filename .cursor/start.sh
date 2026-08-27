#!/usr/bin/env bash
#
# Per-boot reconciliation for the django-cards example project.
# Ensures the "db_cards" host mapping exists and PostgreSQL is running.
# Idempotent: safe to run on every boot.
#
set -euo pipefail

PGDATA="${PGDATA:-$HOME/pgdata}"
PGBIN="$(ls -d /usr/lib/postgresql/*/bin | sort -V | tail -1)"

# The example settings connect to host "db_cards"; map it to localhost.
grep -q "db_cards" /etc/hosts || echo "127.0.0.1 db_cards" | sudo tee -a /etc/hosts >/dev/null

if "$PGBIN/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1; then
  echo "PostgreSQL already running"
else
  echo "Starting PostgreSQL"
  "$PGBIN/pg_ctl" -D "$PGDATA" -l "$HOME/pg.log" -o "-p 5432 -k /tmp" -w start
fi

# Wait until the server accepts connections before returning.
for _ in $(seq 1 30); do
  if "$PGBIN/pg_isready" -h /tmp -p 5432 -U postgres >/dev/null 2>&1; then
    echo "PostgreSQL is ready"
    exit 0
  fi
  sleep 1
done

echo "PostgreSQL did not become ready in time" >&2
exit 1
