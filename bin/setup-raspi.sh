#!/usr/bin/env bash
# Erstinstallation auf Raspberry Pi 5 (Debian/Raspberry Pi OS).
# Nutzung: bash bin/setup-raspi.sh
# Optional: INSTALL_DIR=~/apps/sudokuheist REPO_URL=git@github.com:Nerathu/SudokuHeist.git
set -euo pipefail

# shellcheck source=lib-common.sh
source "$(dirname "$0")/lib-common.sh"

REPO_URL="${REPO_URL:-git@github.com:Nerathu/SudokuHeist.git}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/sudokuheist}"
BRANCH="${BRANCH:-main}"
SETUP_USER="${SUDO_USER:-${USER:-}}"

if [[ -z "$SETUP_USER" ]]; then
  echo "Fehler: Benutzer nicht ermittelbar." >&2
  exit 1
fi

run_as_user() {
  local cmd="$1"
  if [[ "$(id -un)" == "$SETUP_USER" ]]; then
    bash -c "$cmd"
  else
    sudo -u "$SETUP_USER" -H bash -lc "$cmd"
  fi
}

echo "==> SudokuHeist Raspi-Setup"
echo "    Repo:   $REPO_URL"
echo "    Ziel:   $INSTALL_DIR"
echo "    User:   $SETUP_USER"
echo ""

# --- Docker ---
if ! command -v docker &>/dev/null; then
  echo "==> Docker installieren …"
  curl -fsSL https://get.docker.com | sh
  usermod -aG docker "$SETUP_USER" 2>/dev/null || sudo usermod -aG docker "$SETUP_USER"
  echo "    Docker installiert. Nach dem Setup ggf. neu einloggen (docker-Gruppe)."
else
  echo "==> Docker bereits vorhanden"
fi

if ! docker compose version &>/dev/null; then
  echo "Fehler: Docker Compose Plugin fehlt." >&2
  echo "  sudo apt-get update && sudo apt-get install -y docker-compose-plugin" >&2
  exit 1
fi

# --- Repo ---
if [[ -d "$INSTALL_DIR/.git" ]]; then
  echo "==> Repo existiert — aktualisieren"
  run_as_user "cd '$INSTALL_DIR' && git fetch origin && git checkout '$BRANCH' && git pull --ff-only origin '$BRANCH'"
else
  echo "==> Repo klonen"
  run_as_user "git clone --branch '$BRANCH' '$REPO_URL' '$INSTALL_DIR'"
fi

if [[ ! -f "$INSTALL_DIR/.env" ]]; then
  ensure_env_file "$INSTALL_DIR"
fi

# --- Build & Start ---
echo "==> Container bauen und starten"
check_port_for_deploy "$INSTALL_DIR"
run_as_user "cd '$INSTALL_DIR' && docker compose up -d --build --remove-orphans"

PORT="$(read_host_port "$INSTALL_DIR")"
if ! verify_health "$PORT"; then
  run_as_user "cd '$INSTALL_DIR' && docker compose ps" || true
  exit 1
fi

# --- systemd (optional, braucht sudo) ---
if command -v systemctl &>/dev/null; then
  SERVICE_FILE="/etc/systemd/system/sudokuheist.service"
  echo "==> systemd-Service installieren ($SERVICE_FILE)"
  sed "s|__INSTALL_DIR__|$INSTALL_DIR|g" "$INSTALL_DIR/deploy/sudokuheist.service" | sudo tee "$SERVICE_FILE" >/dev/null
  sudo systemctl daemon-reload
  sudo systemctl enable sudokuheist.service
  echo "    Autostart aktiviert: sudokuheist.service"
fi

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
PORT="$(read_host_port "$INSTALL_DIR")"
echo ""
echo "============================================"
echo " SudokuHeist ist bereit."
echo " URL:    $(game_url "${IP:-<raspi-ip>}" "$PORT")"
echo " Health: $(health_url "${IP:-<raspi-ip>}" "$PORT")"
echo ""
echo " Updates vom Entwicklungs-PC:"
echo "   1. git push"
echo "   2. auf dem Raspi: cd $INSTALL_DIR && bash bin/deploy.sh"
echo "============================================"

if ! groups "$SETUP_USER" | grep -q docker; then
  echo ""
  echo "Hinweis: User $SETUP_USER ist noch nicht in der docker-Gruppe."
  echo "  sudo usermod -aG docker $SETUP_USER && neu einloggen"
fi
