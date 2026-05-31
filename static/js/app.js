import { api } from "./api.js";
import { handleEvents, screenShake } from "./fx.js";
import { initGrid, renderGrid, flashCell } from "./grid.js";
import {
  showRaccoon,
  showScreen,
  showToast,
  updateHud,
  renderMetaPanel,
} from "./hud.js";
import { renderMap, renderShop } from "./shop.js";

let currentState = null;
let victoryTimer = null;
let victoryKey = null;

export async function handleStateUpdate(state) {
  currentState = state;
  window.__lastState = state;
  routeScreen(state);
  updateHud(state);
  if (state.last_quote) showRaccoon(state.last_quote);
  if (state.events) {
    handleEvents(state.events);
    state.events.forEach((ev) => {
      const toastMs = ev.type === "kniff_drop" ? 2800 : 1800;
      if (ev.message) showToast(ev.message, toastMs);
      if (ev.type === "cell_correct") flashCell(ev.row, ev.col, "correct");
      if (ev.type === "cell_wrong") flashCell(ev.row, ev.col, "wrong");
      if (ev.type === "auto_fill") flashCell(ev.row, ev.col, "auto");
      if (ev.type === "combo_break") showToast("Combo gebrochen!");
      if (ev.type === "heart_lost") showToast("Herz verloren!");
      if (ev.type === "target_met") showRaccoon(ev.message || "Beute gesichert!");
      if (ev.type === "ante_won") showRaccoon(ev.message || "Gitter geknackt!");
    });
  }
}

function victorySessionKey(state) {
  return `${state.run_seed}-${state.map_index}-${state.antes_completed}`;
}

function hideVictoryOverlay() {
  const overlay = document.getElementById("victoryOverlay");
  if (overlay) overlay.hidden = true;
}

function handleVictoryPhase(state) {
  const overlay = document.getElementById("victoryOverlay");
  if (!overlay) return;

  if (state.phase !== "ante_victory") {
    hideVictoryOverlay();
    victoryKey = null;
    if (victoryTimer) {
      clearTimeout(victoryTimer);
      victoryTimer = null;
    }
    return;
  }

  const key = victorySessionKey(state);
  if (victoryKey === key) return;
  victoryKey = key;

  document.getElementById("victoryMessage").textContent =
    state.victory?.message || "Gitter geknackt!";
  document.getElementById("victoryBeute").textContent = state.victory?.beute_gain ?? 0;
  overlay.hidden = false;

  if (victoryTimer) clearTimeout(victoryTimer);
  victoryTimer = setTimeout(async () => {
    victoryTimer = null;
    hideVictoryOverlay();
    try {
      const next = await api.advanceVictory();
      await handleStateUpdate(next);
    } catch (e) {
      showToast(e.message);
    }
  }, 10000);
}

function routeScreen(state) {
  switch (state.phase) {
    case "map":
      renderMap(state);
      showScreen("Map");
      break;
    case "ante":
    case "ante_victory":
      renderGrid(state);
      showScreen("Puzzle");
      if (state.ante?.is_boss) {
        document.querySelector(".screen-puzzle")?.classList.add("boss");
        if (state.phase === "ante") screenShake();
      } else {
        document.querySelector(".screen-puzzle")?.classList.remove("boss");
      }
      handleVictoryPhase(state);
      break;
    case "shop":
      renderShop(state);
      showScreen("Shop");
      break;
    case "run_over":
    case "run_won":
      showResult(state);
      showScreen("Result");
      break;
    default:
      break;
  }
}

function showResult(state) {
  const won = state.result?.won;
  document.getElementById("resultTitle").textContent = won ? "RUN GEWONNEN!" : "Run vorbei";
  document.getElementById("resultMessage").textContent = state.result?.message || "";
  document.getElementById("resultMeta").textContent = state.result?.meta_reward || 0;
  document.getElementById("resultCard").className = won ? "result-card win" : "result-card lose";
}

async function refreshMeta() {
  try {
    const meta = await api.meta();
    renderMetaPanel(meta);
    document.getElementById("btnContinue").hidden = !meta.has_run;
    return meta;
  } catch (e) {
    showToast(`Meta laden fehlgeschlagen: ${e.message || e}`);
    document.getElementById("btnContinue").hidden = true;
    return null;
  }
}

async function boot() {
  initGrid(
    async (row, col, value) => {
      const state = await api.placeCell(row, col, value);
      await handleStateUpdate(state);
    },
    handleStateUpdate,
  );
  window.__sudokuHeistUpdate = handleStateUpdate;

  document.getElementById("btnNewRun").addEventListener("click", async () => {
    const btn = document.getElementById("btnNewRun");
    const label = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Startet…";
    try {
      await api.newRun();
      const state = await api.startRun();
      await handleStateUpdate(state);
    } catch (e) {
      showToast(e.message || String(e));
      console.error("Neuer Run fehlgeschlagen:", e);
    } finally {
      btn.disabled = false;
      btn.textContent = label;
    }
  });

  document.getElementById("btnContinue").addEventListener("click", async () => {
    try {
      const state = await api.runState();
      await handleStateUpdate(state);
    } catch (e) {
      showToast(e.message || String(e));
    }
  });

  document.getElementById("btnStartAnte").addEventListener("click", async () => {
    try {
      const state = await api.startRun();
      await handleStateUpdate(state);
    } catch (e) {
      showToast(e.message || String(e));
    }
  });

  document.getElementById("btnShopReroll").addEventListener("click", async () => {
    try {
      const state = await api.shopReroll();
      await handleStateUpdate(state);
    } catch (e) {
      showToast(e.message);
    }
  });

  document.getElementById("btnShopContinue").addEventListener("click", async () => {
    const state = await api.anteContinue();
    await handleStateUpdate(state);
  });

  document.getElementById("btnBackHome").addEventListener("click", async () => {
    showScreen("Start");
    document.getElementById("hud").hidden = true;
    document.getElementById("raccoonBubble").hidden = true;
    await refreshMeta();
  });

  await refreshMeta();
  const ver = document.getElementById("appVersion");
  if (ver) ver.textContent = `v${window.__APP_VERSION__ || "?"}`;
  showRaccoon("Willkommen im Tresor. Sudoku ist nur Alibi.");
}

boot().catch((e) => {
  console.error("Boot fehlgeschlagen:", e);
  showToast(`Start fehlgeschlagen: ${e.message || e}`);
});
