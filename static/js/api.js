const BASE = (window.__BASE_PATH__ || "").replace(/\/$/, "");

const API = {
  async get(path) {
    const res = await fetch(`${BASE}${path}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || res.statusText);
    }
    return res.json();
  },
  async post(path, body) {
    const res = await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || res.statusText);
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
  advanceVictory: () => API.post("/api/ante/advance"),
  shopBuy: (item_id, kind) => API.post("/api/shop/buy", { item_id, kind }),
  shopReroll: () => API.post("/api/shop/reroll"),
  anteContinue: () => API.post("/api/ante/continue"),
  useKniff: (item_id) => API.post(`/api/kniff/use?item_id=${encodeURIComponent(item_id)}`),
  metaBuy: (upgrade_id) => API.post("/api/meta/buy", { upgrade_id }),
  buyBoost: (boost_id, row, col) =>
    API.post("/api/ante/boost", { boost_id, row: row ?? null, col: col ?? null }),
};
