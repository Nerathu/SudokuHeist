# SudokuHeist

Balatro trifft Sudoku — ein Roguelike-Browsergame fürs Heimnetz.

Fülle Gitter, stapel Tricks, plündere Tresore. Läuft in Docker auf dem Raspberry Pi; vom Handy im WLAN erreichbar.

## Status

| Bereich | Stand |
|---------|--------|
| MVP | spielbar (Map → Antes → Shop → Boss) |
| Tests | pytest, 13 Tests |
| Deploy | Docker Compose + Nginx, **`/sudokuheist/`** auf Port **8787** (`.env`) |
| Review | **offen** — siehe unten |

## Quick Start

```bash
git clone git@github.com:Nerathu/SudokuHeist.git
cd SudokuHeist
cp .env.example .env   # optional: HOST_PORT anpassen
docker compose up -d --build
```

Dann im Browser (PC oder Handy im gleichen WLAN):

```
http://localhost:8787/sudokuheist/
http://<raspi-ip>:8787/sudokuheist/
```

Health-Check: `http://localhost:8787/sudokuheist/health`

> Standard-Port ist **8787** (`.env` → `HOST_PORT`). Port 80 ist auf dem Raspi oft schon belegt.

## Spielprinzip

| Phase | Was passiert |
|-------|----------------|
| **Map** | Route mit Tresoren, Shops und Boss |
| **Ante** | Sudoku spielen, Punkteziel sichern, Gitter zu Ende füllen |
| **Ante Victory** | 10s Overlay „GEWONNEN“, dann weiter |
| **Shop** | Tricks und Kniffe für Beute kaufen |
| **Meta** | Permanente Upgrades zwischen Runs |

### Ante-Ablauf

1. **Punkteziel** erreichen → Beute gesichert, Boosts freigeschaltet (50/50, Einblick, +5 Züge).
2. **Gitter vollständig** lösen → Ante endet (nicht schon beim Punkteziel).
3. **10 Sekunden** Gewonnen-Overlay, danach Shop oder nächstes Ante.

### Regeln (Kurz)

- **Herzen**: Falsche Zahl kostet ein Herz (3 Start, erweiterbar).
- **Beute**: Währung für Shop zwischen Antes.
- **Tricks**: Passive Joker (12 im MVP).
- **Kniffe**: Einmal-Items (4 im MVP).
- **Auto-Fill**: Wenn in Reihe/Spalte/Block nur noch eine Zahl fehlt, wird sie gesetzt.
- **Falsche Zellen**: Rot markiert; per ✕ löschen oder mit neuer Zahl überschreiben.

## UI (Mobile)

- Puzzle-Modus: volle Viewport-Höhe, kein Scrollen.
- Numpad 2×5, vollständige Ziffern ausgegraut.
- 50/50: zwei Kandidaten diagonal in der Zelle (Ecke antippen).
- Fortschrittsbalken: erst Punkte bis Shop, dann Gitter-Fortschritt.

## Entwicklung lokal (auch fürs Handy im WLAN)

```bash
bash bin/dev.sh
```

Standard: **`0.0.0.0:8787`**, Pfad **`/sudokuheist/`**:

```
http://localhost:8787/sudokuheist/
http://<deine-lan-ip>:8787/sudokuheist/
```

Wichtig: Ohne `--host 0.0.0.0` lauscht uvicorn nur auf `127.0.0.1` — dann geht die LAN-IP **nicht**.

Alternativ manuell:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DB_PATH=/tmp/sudokuheist.db
export BASE_PATH=/sudokuheist
uvicorn app.main:app --reload --host 0.0.0.0 --port 8787
```

Tests:

```bash
python -m pytest -q
```

Frontend-Dev: `http://localhost:8787/sudokuheist/`

## API

Basis-Pfad: **`/sudokuheist`** (über Env `BASE_PATH` änderbar). Alle Endpunkte darunter:

| Endpoint | Beschreibung |
|----------|--------------|
| `GET /sudokuheist/health` | Status |
| `GET /sudokuheist/api/meta` | Meta-Beute + Upgrades |
| `POST /sudokuheist/api/run/new` | Neuer Run |
| `POST /sudokuheist/api/run/start` | Erstes Ante starten |
| `GET /sudokuheist/api/run/state` | Aktueller Run |
| `POST /sudokuheist/api/cell/place` | Zelle setzen (falsche Zellen überschreibbar) |
| `POST /sudokuheist/api/cell/clear` | Falsche Zelle löschen |
| `POST /sudokuheist/api/ante/boost` | In-Run-Boost kaufen (50/50, Einblick, +5 Züge) |
| `POST /sudokuheist/api/ante/advance` | Nach Sieg-Overlay: Shop / nächstes Ante |
| `POST /sudokuheist/api/shop/buy` | Item kaufen |
| `POST /sudokuheist/api/shop/reroll` | Shop rerollen |
| `POST /sudokuheist/api/ante/continue` | Shop verlassen |
| `POST /sudokuheist/api/kniff/use` | Kniff einsetzen |
| `POST /sudokuheist/api/meta/buy` | Meta-Upgrade |

### Run-Phasen (`phase` im State)

| Phase | Bedeutung |
|-------|-----------|
| `map` | Routenauswahl |
| `ante` | Aktives Sudoku |
| `ante_victory` | Gitter gelöst, wartet auf Advance (Frontend: 10s Overlay) |
| `shop` | Schwarzmarkt |
| `run_over` / `run_won` | Run beendet |

## Raspberry Pi 5 — Deploy via Git

Repo: **https://github.com/Nerathu/SudokuHeist**

### Erstinstallation (einmalig auf dem Raspi)

SSH-Key für GitHub auf dem Raspi hinterlegen, dann:

```bash
curl -fsSL https://raw.githubusercontent.com/Nerathu/SudokuHeist/main/bin/setup-raspi.sh | bash
```

Oder manuell:

```bash
git clone git@github.com:Nerathu/SudokuHeist.git ~/sudokuheist
cd ~/sudokuheist
bash bin/setup-raspi.sh
```

Das Script installiert Docker (falls nötig), klont das Repo nach `~/sudokuheist`, startet die Container und richtet **systemd** (`sudokuheist.service`) für Autostart ein.

Spiel im LAN: **`http://<raspi-ip>:8787/sudokuheist/`**

Port ändern: in `~/sudokuheist/.env` → `HOST_PORT=9090`, dann `bash bin/deploy.sh`

### Updates (nach jedem `git push` vom Dev-PC)

Auf dem Raspi:

```bash
cd ~/sudokuheist
bash bin/deploy.sh
```

Workflow:

1. Lokal entwickeln → `git commit` → `git push`
2. Auf dem Raspi: `bash bin/deploy.sh` (pull + rebuild)
3. GitHub Actions laufen pytest bei jedem Push

### Optionen (Env)

| Variable | Default | Bedeutung |
|----------|---------|-----------|
| `HOST_PORT` | `8787` | Host-Port in `.env` (Docker → Nginx) |
| `INSTALL_DIR` | `~/sudokuheist` | Installationspfad |
| `REPO_URL` | `git@github.com:Nerathu/SudokuHeist.git` | Git-Remote |
| `BRANCH` | `main` | Branch |

## Raspi-Hinweise

- Erreichbar unter **`http://<raspi-ip>:8787/sudokuheist/`** (Port in `.env`)
- Daten liegen im Volume `sudokuheist_data` (SQLite)
- Image basiert auf `python:3.12-slim` — ARM64-tauglich
- Kein Internet nötig nach dem Build (keine CDN-Fonts)

### Anderen Port nutzen

```bash
echo 'HOST_PORT=9090' >> ~/sudokuheist/.env
cd ~/sudokuheist && bash bin/deploy.sh
```

## Stack

- FastAPI + SQLite
- Vanilla JS (mobile-first)
- Docker Compose (App + Nginx)

## Offenes Review

> **TODO: Code- und Gameplay-Review** — nach erstem Handy-Test auf dem Raspi.

Prüfpunkte:

- [ ] Balancing: Punkteziele, Zuglimit, Beute, Shop-Preise, Boss-Schwierigkeit
- [ ] UX am Handy: Gittergröße, Numpad, Sieg-Overlay, Fehlerkorrektur
- [ ] Edge Cases: Reload während `ante_victory`, Radiergummi-Flow, Auto-Fill + Sieg
- [ ] API/State: Persistenz, doppeltes `_persist`, Phase-Übergänge
- [ ] Deploy: Docker auf ARM, Volume-Backup, Port-Firewall
- [ ] Tests: Abdeckung für volle Ante-/Boss-Completion (optional)
