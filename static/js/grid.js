import { showToast, vibrate } from "./hud.js";

let selected = null;
let onPlace = null;
let onStateUpdate = null;
let pendingBoost = null;
let activeHintOptions = null;
let intelMode = false;
let intelScanDigit = null;
let intelToggleBound = false;

export function initGrid(handler, stateHandler) {
  onPlace = handler;
  onStateUpdate = stateHandler;
  buildNumpad();
  bindIntelToggle();
}

export function setPendingBoost(boostId) {
  pendingBoost = boostId;
  showToast(
    boostId === "fifty_fifty"
      ? "50/50: Leere Zelle antippen"
      : boostId === "reveal"
        ? "Einblick: Zelle antippen"
        : "Boost aktiv",
  );
}

function isWrongCell(r, c, state) {
  if (!state?.ante) return false;
  return (state.ante.wrong_cells || []).some(([wr, wc]) => wr === r && wc === c);
}

function validCandidatesForCell(grid, row, col) {
  if (grid[row][col] !== 0) return [];
  const seen = new Set();
  for (let i = 0; i < 9; i++) {
    if (grid[row][i]) seen.add(grid[row][i]);
    if (grid[i][col]) seen.add(grid[i][col]);
  }
  const br = Math.floor(row / 3) * 3;
  const bc = Math.floor(col / 3) * 3;
  for (let r = br; r < br + 3; r++) {
    for (let c = bc; c < bc + 3; c++) {
      if (grid[r][c]) seen.add(grid[r][c]);
    }
  }
  return [1, 2, 3, 4, 5, 6, 7, 8, 9].filter((n) => !seen.has(n));
}

function filterIntelNotes(grid, row, col, notes) {
  if (!notes?.length) return [];
  const allowed = new Set(validCandidatesForCell(grid, row, col));
  return notes.filter((n) => allowed.has(n));
}

function bindIntelToggle() {
  if (intelToggleBound) return;
  const btn = document.getElementById("intelToggle");
  if (!btn) return;
  intelToggleBound = true;
  btn.addEventListener("click", async () => {
    intelMode = !intelMode;
    intelScanDigit = null;
    btn.setAttribute("aria-pressed", String(intelMode));
    syncIntelChrome();
    if (intelMode) {
      const state = window.__lastState;
      if (state?.ante?.intel_enabled) {
        const { api } = await import("./api.js");
        try {
          const result = await api.syncIntel();
          if (onStateUpdate) onStateUpdate(result);
        } catch (err) {
          intelMode = false;
          btn.setAttribute("aria-pressed", "false");
          syncIntelChrome();
          showToast(err.message);
          return;
        }
      }
      showToast("WIRETAP aktiv — nur mögliche Kandidaten");
      vibrate(12);
    }
  });
}

function syncIntelChrome() {
  const puzzle = document.querySelector(".screen-puzzle");
  puzzle?.classList.toggle("intel-mode", intelMode);
  puzzle?.classList.toggle("intel-scanning", intelScanDigit != null);
  document.getElementById("intelToggle")?.setAttribute("aria-pressed", String(intelMode));
}

function updateIntelButton(state) {
  const btn = document.getElementById("intelToggle");
  if (!btn) return;
  const enabled = state?.ante?.intel_enabled && state?.phase === "ante";
  if (!enabled) {
    btn.hidden = true;
    intelMode = false;
    intelScanDigit = null;
    syncIntelChrome();
    return;
  }
  btn.hidden = false;
  syncIntelChrome();
}

function renderIntelCell(cell, notes, scanDigit = intelScanDigit) {
  cell.classList.add("intel-cell");
  const grid = document.createElement("span");
  grid.className = "intel-grid";
  for (let d = 1; d <= 9; d++) {
    const span = document.createElement("span");
    span.className = `intel-n intel-n${d}`;
    if (notes.includes(d)) {
      span.textContent = d;
      span.classList.add("active");
      if (scanDigit === d) span.classList.add("intel-n-highlight");
    }
    grid.appendChild(span);
  }
  cell.appendChild(grid);
}

function applyIntelScan(digit, state) {
  intelScanDigit = digit;
  syncIntelChrome();
  const intel = state?.ante?.intel || {};
  const grid = state?.ante?.player_grid;
  document.querySelectorAll(".cell").forEach((cell) => {
    cell.classList.remove("intel-match");
    const r = Number(cell.dataset.row);
    const c = Number(cell.dataset.col);
    const notes = filterIntelNotes(grid, r, c, intel[`${r},${c}`] || []);
    if (notes.includes(digit)) {
      cell.classList.add("intel-match");
      cell.querySelectorAll(".intel-grid span").forEach((span) => {
        span.classList.toggle("intel-n-highlight", Number(span.textContent) === digit);
      });
    }
  });
  document.querySelectorAll(".num-btn[data-value]").forEach((btn) => {
    btn.classList.toggle("intel-scan", Number(btn.dataset.value) === digit);
  });
  vibrate(8);
}

function clearIntelScan() {
  intelScanDigit = null;
  syncIntelChrome();
  document.querySelectorAll(".cell.intel-match").forEach((c) => c.classList.remove("intel-match"));
  document.querySelectorAll(".intel-n-highlight").forEach((s) => s.classList.remove("intel-n-highlight"));
  document.querySelectorAll(".num-btn.intel-scan").forEach((b) => b.classList.remove("intel-scan"));
}

function buildNumpad() {
  const pad = document.getElementById("numpad");
  pad.innerHTML = "";
  for (let n = 1; n <= 9; n++) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "num-btn";
    btn.dataset.value = n;
    btn.textContent = n;
    btn.addEventListener("click", () => placeNumber(n));
    pad.appendChild(btn);
  }
  const clear = document.createElement("button");
  clear.type = "button";
  clear.className = "num-btn clear";
  clear.textContent = "✕";
  clear.addEventListener("click", async () => {
    if (!selected) {
      activeHintOptions = null;
      document.querySelectorAll(".cell.selected").forEach((c) => c.classList.remove("selected"));
      updateNumpadFilter(window.__lastState?.ante?.player_grid);
      return;
    }
    const state = window.__lastState;
    if (isWrongCell(selected.r, selected.c, state)) {
      const { api } = await import("./api.js");
      try {
        const result = await api.clearCell(selected.r, selected.c);
        selected = null;
        activeHintOptions = null;
        if (onStateUpdate) onStateUpdate(result);
      } catch (err) {
        showToast(err.message);
      }
      return;
    }
    selected = null;
    activeHintOptions = null;
    document.querySelectorAll(".cell.selected").forEach((c) => c.classList.remove("selected"));
    updateNumpadFilter(window.__lastState?.ante?.player_grid);
  });
  pad.appendChild(clear);
}

function digitCounts(grid) {
  const counts = Array(10).fill(0);
  if (!grid) return counts;
  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < 9; c++) {
      const v = grid[r][c];
      if (v >= 1 && v <= 9) counts[v]++;
    }
  }
  return counts;
}

function updateNumpadFilter(grid, hintOptions = activeHintOptions) {
  const counts = digitCounts(grid);
  document.querySelectorAll(".num-btn[data-value]").forEach((btn) => {
    const val = Number(btn.dataset.value);
    const complete = counts[val] >= 9;
    btn.classList.toggle("num-complete", complete);
    btn.classList.remove("hint-option");

    if (hintOptions) {
      const allowed = hintOptions.includes(val);
      btn.disabled = complete || !allowed;
      btn.classList.toggle("hint-option", allowed);
    } else {
      btn.disabled = complete;
    }
  });
}

function pickHintTriangle(e, [bottomLeft, topRight]) {
  const rect = e.currentTarget.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  const topRightHalf = y < rect.height - (rect.height / rect.width) * x;
  return topRightHalf ? topRight : bottomLeft;
}

function renderHintCell(cell, pair) {
  cell.classList.add("hint-split");
  cell.innerHTML = `
    <span class="hint-bl">${pair[0]}</span>
    <span class="hint-tr">${pair[1]}</span>
    <span class="hint-diagonal" aria-hidden="true"></span>
  `;
}

export function renderGrid(state) {
  const gridEl = document.getElementById("sudokuGrid");
  gridEl.innerHTML = "";
  const grid = state.ante.player_grid;
  const fixed = state.ante.fixed;
  const hints = state.ante.hints || {};
  const intel = state.ante.intel || {};
  const wrongSet = new Set((state.ante.wrong_cells || []).map(([r, c]) => `${r},${c}`));
  const prevSelected = selected;
  selected = null;
  activeHintOptions = null;

  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < 9; c++) {
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = "cell";
      cell.dataset.row = r;
      cell.dataset.col = c;
      cell.setAttribute("role", "gridcell");
      if ((c + 1) % 3 === 0 && c < 8) cell.classList.add("border-r");
      if ((r + 1) % 3 === 0 && r < 8) cell.classList.add("border-b");

      const val = grid[r][c];
      const hintKey = `${r},${c}`;
      const intelNotes = intel[hintKey] || [];

      if (!val && hints[hintKey]) {
        renderHintCell(cell, hints[hintKey]);
      } else if (!val && intelMode && state.ante.intel_enabled) {
        const filteredNotes = filterIntelNotes(grid, r, c, intelNotes);
        if (filteredNotes.length) renderIntelCell(cell, filteredNotes);
      } else {
        cell.textContent = val || "";
      }

      if (fixed[r][c]) cell.classList.add("fixed");
      if (val) cell.classList.add("filled");
      if (wrongSet.has(`${r},${c}`)) cell.classList.add("wrong");

      cell.addEventListener("click", (e) => onCellClick(e, r, c, fixed[r][c], state));
      gridEl.appendChild(cell);
    }
  }

  if (prevSelected) {
    selectCell(prevSelected.r, prevSelected.c, state, false);
  }
  if (intelScanDigit != null) {
    applyIntelScan(intelScanDigit, state);
  }

  updateIntelButton(state);
  renderTricks(state);
  renderKniffs(state);
  renderBoosts(state);
  renderShopProgress(state);
  renderAnteStatus(state);
  updateNumpadFilter(grid);
}

function renderShopProgress(state) {
  const label = document.getElementById("shopProgressLabel");
  const value = document.getElementById("shopProgressValue");
  const fill = document.getElementById("shopProgressFill");
  const track = fill?.parentElement;
  if (!label || !value || !fill) return;

  const a = state.ante;
  const shopName = a.next_shop_label || "Shop";

  if (a.target_met) {
    const pct = Math.round((a.puzzle_progress || 0) * 100);
    fill.style.width = `${pct}%`;
    fill.className = "shop-progress-fill puzzle-phase";
    label.textContent = `Gitter fertig → ${shopName}`;
    value.textContent = `${a.cells_remaining} Felder offen`;
    if (track) track.setAttribute("aria-valuenow", String(pct));
  } else {
    const pct = Math.round((a.score_progress || 0) * 100);
    fill.style.width = `${pct}%`;
    fill.className = "shop-progress-fill score-phase";
    label.textContent = `Noch ${a.points_to_target} Punkte bis ${shopName}`;
    value.textContent = `${a.score} / ${a.score_target}`;
    if (track) track.setAttribute("aria-valuenow", String(pct));
  }
}

function renderAnteStatus(state) {
  const bar = document.getElementById("anteStatus");
  if (!bar) return;
  const a = state.ante;
  if (a.target_met) {
    bar.className = "ante-status secured";
    bar.textContent = `Beute gesichert · noch ${a.cells_remaining} Felder · Punkte für Boosts nutzbar`;
  } else {
    bar.className = "ante-status";
    bar.textContent = `Noch ${a.cells_remaining} Felder · Ziel: ${a.score_target} Punkte`;
  }
}

function renderBoosts(state) {
  const bar = document.getElementById("boostsBar");
  if (!bar) return;
  bar.innerHTML = "";
  if (!state.ante.target_met) {
    bar.hidden = true;
    return;
  }
  bar.hidden = false;
  (state.ante.boosts || []).forEach((boost) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "boost-btn";
    const affordable = state.ante.score - boost.cost >= state.ante.score_target;
    btn.disabled = !affordable;
    btn.innerHTML = `<strong>${boost.name}</strong><span>${boost.cost} Pkt</span>`;
    btn.title = boost.description;
    btn.addEventListener("click", async () => {
      if (boost.id === "extra_moves") {
        const { api } = await import("./api.js");
        try {
          const result = await api.buyBoost(boost.id);
          if (onStateUpdate) onStateUpdate(result);
        } catch (e) {
          showToast(e.message);
        }
      } else {
        setPendingBoost(boost.id);
      }
    });
    bar.appendChild(btn);
  });
}

async function onCellClick(e, r, c, isFixed, state) {
  if (state.pending_kniff === "radiergummi" && !isFixed && isWrongCell(r, c, state)) {
    const { api } = await import("./api.js");
    try {
      const result = await api.clearCell(r, c);
      if (onStateUpdate) onStateUpdate(result);
    } catch (err) {
      showToast(err.message);
    }
    return;
  }

  if (pendingBoost && !isFixed && state.ante.player_grid[r][c] === 0) {
    const { api } = await import("./api.js");
    try {
      const result = await api.buyBoost(pendingBoost, r, c);
      pendingBoost = null;
      if (onStateUpdate) onStateUpdate(result);
    } catch (err) {
      showToast(err.message);
    }
    return;
  }

  const hintKey = `${r},${c}`;
  const hints = state.ante.hints || {};
  if (!isFixed && state.ante.player_grid[r][c] === 0 && hints[hintKey]) {
    const value = pickHintTriangle(e, hints[hintKey]);
    try {
      await onPlace(r, c, value);
      activeHintOptions = null;
      vibrate(20);
    } catch (err) {
      showToast(err.message);
    }
    return;
  }

  if (isFixed) return;
  if (state.ante.player_grid[r][c] !== 0 && !isWrongCell(r, c, state)) return;
  selectCell(r, c);
}

function selectCell(r, c, state = window.__lastState, vibrateOn = true) {
  selected = { r, c };
  const key = `${r},${c}`;
  const hints = state?.ante?.hints || {};
  activeHintOptions = hints[key] || null;
  document.querySelectorAll(".cell").forEach((el) => el.classList.remove("selected"));
  document.querySelectorAll(".cell")[r * 9 + c]?.classList.add("selected");
  updateNumpadFilter(state?.ante?.player_grid, activeHintOptions);
  if (vibrateOn) vibrate(10);
}

async function placeNumber(n) {
  const state = window.__lastState;

  if (intelMode && state?.ante?.intel_enabled) {
    if (selected) {
      const { r, c } = selected;
      if (state.ante.fixed[r][c]) return;
      if (state.ante.player_grid[r][c] !== 0 && !isWrongCell(r, c, state)) return;
      const { api } = await import("./api.js");
      try {
        const result = await api.toggleIntelNote(r, c, n);
        if (onStateUpdate) onStateUpdate(result);
        vibrate(16);
      } catch (err) {
        showToast(err.message);
      }
      return;
    }
    if (intelScanDigit === n) {
      clearIntelScan();
      return;
    }
    applyIntelScan(n, state);
    return;
  }

  if (!selected || !onPlace) return;
  if (activeHintOptions && !activeHintOptions.includes(n)) {
    showToast("Nur die zwei 50/50-Zahlen!");
    return;
  }
  const counts = digitCounts(window.__lastState?.ante?.player_grid);
  if (!activeHintOptions && counts[n] >= 9) {
    showToast(`${n} ist schon vollständig im Gitter.`);
    return;
  }
  try {
    await onPlace(selected.r, selected.c, n);
    activeHintOptions = null;
    pendingBoost = null;
    vibrate(20);
  } catch (err) {
    showToast(err.message);
  }
}

function renderTricks(state) {
  const bar = document.getElementById("tricksBar");
  bar.innerHTML = "";
  (state.tricks || []).filter(Boolean).forEach((t) => {
    const chip = document.createElement("span");
    chip.className = "trick-chip";
    chip.title = t.description;
    chip.textContent = t.name;
    bar.appendChild(chip);
  });
}

function renderKniffs(state) {
  const bar = document.getElementById("kniffsBar");
  bar.innerHTML = "";
  Object.entries(state.kniffs || {}).forEach(([id, count]) => {
    if (count <= 0) return;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "kniff-btn";
    btn.textContent = `${id.replace(/_/g, " ")} (${count})`;
    btn.addEventListener("click", async () => {
      const { api } = await import("./api.js");
      try {
        const result = await api.useKniff(id);
        if (onStateUpdate) onStateUpdate(result);
      } catch (err) {
        showToast(err.message);
      }
    });
    bar.appendChild(btn);
  });
}

export function flashCell(row, col, kind = "correct") {
  const idx = row * 9 + col;
  const cell = document.querySelectorAll(".cell")[idx];
  if (!cell) return;
  if (kind === "wrong") {
    cell.classList.add("flash-wrong", "wrong");
    setTimeout(() => cell.classList.remove("flash-wrong"), 450);
    return;
  }
  if (kind === "auto") {
    cell.classList.add("auto-fill");
    setTimeout(() => cell.classList.remove("auto-fill"), 600);
    return;
  }
  cell.classList.add(kind);
  setTimeout(() => cell.classList.remove(kind), 500);
}
