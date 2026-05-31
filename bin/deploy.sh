#!/usr/bin/env bash
# Auf dem Raspi ausführen: Repo aktualisieren und Container neu bauen.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BRANCH="${BRANCH:-main}"

echo "==> SudokuHeist deploy (${ROOT})"
git fetch origin
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

if ! docker compose version &>/dev/null; then
  echo "Fehler: docker compose nicht gefunden. Bitte bin/setup-raspi.sh ausführen." >&2
  exit 1
fi

docker compose up -d --build --remove-orphans

echo ""
echo "Deploy fertig."
echo "  Spiel:  http://$(hostname -I | awk '{print $1}')/sudokuheist/"
echo "  Health: http://$(hostname -I | awk '{print $1}')/sudokuheist/health"
