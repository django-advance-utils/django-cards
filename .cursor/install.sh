#!/usr/bin/env bash
#
# Idempotent dependency setup for the django-cards development environment.
# Runs after the repository is checked out. Installs the system toolchain the
# project pins (Python 3.11 + PostgreSQL) and the Python dependencies.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# --- System toolchain (Django 3.2 requires Python 3.11; app uses PostgreSQL) ---
if ! command -v python3.11 >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt-get update
    sudo apt-get install -y python3.11 python3.11-venv python3.11-dev
fi

if ! command -v psql >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y postgresql postgresql-contrib
fi

# --- Python virtual environment ---
if [ ! -x "$REPO_ROOT/.venv/bin/python" ]; then
    python3.11 -m venv "$REPO_ROOT/.venv"
fi
"$REPO_ROOT/.venv/bin/pip" install --upgrade pip
"$REPO_ROOT/.venv/bin/pip" install -r "$REPO_ROOT/requirements.txt"
