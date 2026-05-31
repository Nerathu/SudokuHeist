function resolveApiUrl(path) {
  const clean = path.startsWith("/") ? path : `/${path}`;
  let base = window.__BASE_PATH__;
  if (!base || base.includes("@@")) {
    const match = window.location.pathname.match(/^(.*\/sudokuheist)/);
    base = match ? match[1] : "";
  }
  return `${base.replace(/\/$/, "")}${clean}`;
}

function apiErrorMessage(err, statusText) {
  if (!err) return statusText || "Unbekannter Fehler";
  if (typeof err.detail === "string") return err.detail;
  if (Array.isArray(err.detail)) {
    return err.detail.map((e) => e.msg || JSON.stringify(e)).join("; ");
  }
  if (typeof err.detail === "object" && err.detail !== null) {
    return JSON.stringify(err.detail);
  }
  return statusText || "Unbekannter Fehler";
}

const API = {
  async get(path) {
    const res = await fetch(resolveApiUrl(path));
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(apiErrorMessage(err, res.statusText));
    }
    return res.json();
  },
  async post(path, body = {}) {
    const res = await fetch(resolveApiUrl(path), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(apiErrorMessage(err, res.statusText));
    }
    return res.json();
  },
};

export const api = {
  meta: () => API.get("/api/meta"),
  runState: () => API.get("/api/run/state"),
  newRun: (seed) => API.post("/api/run/new", seed != null ? { seed } : {}),
  startRun: () => API.post("/api/run/start"),
  placeCell: (row, col, value) => API.post("/api/cell/place", { row, col, value }),
  clearCell: (row, col) => API.post("/api/cell/clear", { row, col }),
  toggleIntelNote: (row, col, digit) => API.post("/api/cell/intel", { row, col, digit }),
  syncIntel: () => API.post("/api/intel/sync"),
  advanceVictory: () => API.post("/api/ante/advance"),
  shopBuy: (item_id, kind) => API.post("/api/shop/buy", { item_id, kind }),
  shopReroll: () => API.post("/api/shop/reroll"),
  anteContinue: () => API.post("/api/ante/continue"),
  useKniff: (item_id) => API.post(`/api/kniff/use?item_id=${encodeURIComponent(item_id)}`),
  metaBuy: (upgrade_id) => API.post("/api/meta/buy", { upgrade_id }),
  buyBoost: (boost_id, row, col) =>
    API.post("/api/ante/boost", { boost_id, row: row ?? null, col: col ?? null }),
};
