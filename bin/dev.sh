#!/usr/bin/env bash
# Dev-Server: im LAN erreichbar (Handy im gleichen WLAN).
set -euo pipefail
cd "$(dirname "$0")/.."

export DB_PATH="${DB_PATH:-/tmp/sudokuheist.db}"
export BASE_PATH="${BASE_PATH:-/sudokuheist}"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8787}"

echo "SudokuHeist: http://127.0.0.1:${PORT}${BASE_PATH}/"
echo "Im WLAN z.B.: http://$(hostname -I | awk '{print $1}'):${PORT}${BASE_PATH}/"
exec .venv/bin/uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
