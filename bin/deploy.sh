#!/usr/bin/env bash
# Auf dem Raspi ausführen: Repo aktualisieren und Container neu bauen.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib-common.sh
source "$(dirname "$0")/lib-common.sh"
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

check_port_for_deploy "$ROOT"
docker compose up -d --build --force-recreate --remove-orphans

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
PORT="$(read_host_port "$ROOT")"
if ! verify_health "$PORT"; then
  docker compose ps
  exit 1
fi

echo ""
echo "Deploy fertig."
echo "  Spiel:  $(game_url "${IP:-localhost}" "$PORT")"
echo "  Health: $(health_url "${IP:-localhost}" "$PORT")"
