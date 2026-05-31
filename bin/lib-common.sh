#!/usr/bin/env bash
# Gemeinsame Hilfsfunktionen für Deploy-Skripte.

DEFAULT_HOST_PORT=9877

read_host_port() {
  local dir="${1:-.}"
  local port="$DEFAULT_HOST_PORT"
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

port_in_use() {
  local port="$1"
  if command -v ss &>/dev/null; then
    ss -ltn 2>/dev/null | grep -q ":${port} "
    return $?
  fi
  if command -v lsof &>/dev/null; then
    lsof -iTCP:"$port" -sTCP:LISTEN -t &>/dev/null
    return $?
  fi
  return 1
}

find_free_port() {
  local port
  for port in "$DEFAULT_HOST_PORT" 9878 9879 9880 8788 8790 8791; do
    if ! port_in_use "$port"; then
      echo "$port"
      return 0
    fi
  done
  echo "$DEFAULT_HOST_PORT"
}

ensure_env_file() {
  local dir="$1"
  if [[ -f "$dir/.env" ]]; then
    return 0
  fi
  local port
  port="$(find_free_port)"
  echo "HOST_PORT=$port" >"$dir/.env"
  echo "==> .env angelegt (HOST_PORT=$port)"
}

check_port_for_deploy() {
  local dir="$1"
  local port
  port="$(read_host_port "$dir")"
  if ! port_in_use "$port"; then
    return 0
  fi
  if docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null | grep -qE "sudokuheist-nginx.*:${port}->"; then
    return 0
  fi
  echo "FEHLER: Port $port ist schon belegt (vermutlich anderer Dienst, z.B. Dashboard)." >&2
  echo "  In $dir/.env anderen HOST_PORT setzen, z.B. HOST_PORT=$(find_free_port)" >&2
  if command -v ss &>/dev/null; then
    echo "  Belegung:" >&2
    ss -ltnp 2>/dev/null | grep ":${port} " >&2 || true
  fi
  exit 1
}

verify_health() {
  local port="$1"
  local url="http://127.0.0.1:${port}/sudokuheist/health"
  local code body
  for _ in 1 2 3 4 5; do
    body=$(curl -fsS "$url" 2>/dev/null || true)
    if [[ "$body" == *'"ok":true'* ]]; then
      return 0
    fi
    sleep 1
  done
  code=$(curl -s -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || echo "000")
  echo "FEHLER: SudokuHeist antwortet nicht auf Port $port (HTTP $code)." >&2
  echo "  Erwartet: $(health_url localhost "$port")" >&2
  echo "  Port evtl. von anderem Dienst belegt — .env anpassen und erneut deployen." >&2
  return 1
}
