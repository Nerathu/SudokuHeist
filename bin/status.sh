#!/usr/bin/env bash
# Status und Health-Check (auf dem Raspi im Repo-Ordner ausführen).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lib-common.sh
source "$(dirname "$0")/lib-common.sh"
cd "$ROOT"

PORT="$(read_host_port "$ROOT")"
IP="$(hostname -I 2>/dev/null | awk '{print $1}')"

echo "==> SudokuHeist Status"
echo "    Port:   $PORT (.env)"
echo "    URL:    $(game_url "${IP:-localhost}" "$PORT")"
echo ""

echo "==> Docker"
docker compose ps
echo ""

echo "==> Health"
if verify_health "$PORT"; then
  curl -fsS "http://127.0.0.1:${PORT}/sudokuheist/health"
  echo ""
  echo "OK"
else
  exit 1
fi
