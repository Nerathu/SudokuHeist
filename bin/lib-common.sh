#!/usr/bin/env bash
# Gemeinsame Hilfsfunktionen für Deploy-Skripte.

read_host_port() {
  local dir="${1:-.}"
  local port="8787"
  if [[ -f "$dir/.env" ]]; then
    local line
    line=$(grep -E '^HOST_PORT=' "$dir/.env" | tail -1 || true)
    if [[ -n "$line" ]]; then
      port="${line#HOST_PORT=}"
    fi
  fi
  echo "${HOST_PORT:-$port}"
}

game_url() {
  local ip="$1"
  local port="$2"
  echo "http://${ip}:${port}/sudokuheist/"
}

health_url() {
  local ip="$1"
  local port="$2"
  echo "http://${ip}:${port}/sudokuheist/health"
}
