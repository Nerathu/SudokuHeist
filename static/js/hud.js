let toastTimer;

const DIFFICULTY_META = {
  easy: { label: "Leicht", tier: 1 },
  medium: { label: "Mittel", tier: 2 },
  hard: { label: "Schwer", tier: 3 },
  boss: { label: "Boss", tier: 4 },
};

export function showToast(msg, ms = 2200) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), ms);
}

export function vibrate(pattern = 30) {
  if (navigator.vibrate) navigator.vibrate(pattern);
}

export function showRaccoon(text) {
  if (document.body.classList.contains("puzzle-mode")) return;
  const bubble = document.getElementById("raccoonBubble");
  const p = document.getElementById("raccoonText");
  p.textContent = text;
  bubble.hidden = false;
  bubble.classList.remove("pop");
  void bubble.offsetWidth;
  bubble.classList.add("pop");
}

export function renderHearts(current, max) {
  const el = document.getElementById("heartsHud");
  el.innerHTML = "";
  for (let i = 0; i < max; i++) {
    const span = document.createElement("span");
    span.textContent = i < current ? "♥" : "♡";
    span.className = i < current ? "heart full" : "heart empty";
    el.appendChild(span);
  }
}

export function renderDifficulty(state) {
  const badge = document.getElementById("difficultyBadge");
  const label = document.getElementById("difficultyLabel");
  const bars = document.getElementById("difficultyBars");
  if (!badge || !label || !bars) return;

  const inPuzzle = state?.phase === "ante" || state?.phase === "ante_victory";
  const diff = state?.ante?.difficulty;
  if (!inPuzzle || !diff) {
    badge.hidden = true;
    return;
  }

  const meta = DIFFICULTY_META[diff] || { label: diff, tier: 2 };
  badge.hidden = false;
  badge.dataset.tier = diff;
  label.textContent = meta.label;
  bars.innerHTML = "";
  for (let i = 1; i <= 4; i++) {
    const bar = document.createElement("span");
    bar.className = `difficulty-bar${i <= meta.tier ? " active" : ""}`;
    bars.appendChild(bar);
  }
}

export function updateHud(state) {
  document.getElementById("hud").hidden = !state || state.phase === "map" && !state.ante;
  if (!state) return;
  renderHearts(state.hearts, state.max_hearts);
  renderDifficulty(state);
  document.getElementById("beuteHud").textContent = state.beute;
  if (state.ante) {
    document.getElementById("scoreHud").textContent = state.ante.score;
    const inline = document.getElementById("scoreHudInline");
    if (inline) inline.textContent = state.ante.score;
    document.getElementById("targetScore").textContent = state.ante.score_target;
    document.getElementById("movesLeft").textContent = state.ante.moves_left;
    const combo = state.ante.combo_streak || 0;
    document.getElementById("comboDisplay").textContent = combo > 1 ? `Combo ×${Math.min(5, 1 + combo * 0.25).toFixed(2)}` : "Combo ×1";
    document.getElementById("comboDisplay").classList.toggle("hot", combo >= 3);
    renderShopProgressHud(state);
  }
}

function renderShopProgressHud(state) {
  const label = document.getElementById("shopProgressLabel");
  const value = document.getElementById("shopProgressValue");
  const fill = document.getElementById("shopProgressFill");
  if (!label || !fill || state.phase !== "ante") return;
  const a = state.ante;
  const shopName = a.next_shop_label || "Shop";
  if (a.target_met) {
    const pct = Math.round((a.puzzle_progress || 0) * 100);
    fill.style.width = `${pct}%`;
    fill.className = "shop-progress-fill puzzle-phase";
    label.textContent = `Gitter fertig → ${shopName}`;
    if (value) value.textContent = `${a.cells_remaining} Felder offen`;
  } else {
    const pct = Math.round((a.score_progress || 0) * 100);
    fill.style.width = `${pct}%`;
    fill.className = "shop-progress-fill score-phase";
    label.textContent = `Noch ${a.points_to_target} Punkte bis ${shopName}`;
    if (value) value.textContent = `${a.score} / ${a.score_target}`;
  }
}

export function showScreen(name) {
  const screens = ["Start", "Map", "Puzzle", "Shop", "Result"];
  screens.forEach((s) => {
    document.getElementById(`screen${s}`).hidden = s !== name;
  });
  document.body.classList.toggle("puzzle-mode", name === "Puzzle");
  document.querySelector(".app")?.classList.toggle("puzzle-mode", name === "Puzzle");
  const bubble = document.getElementById("raccoonBubble");
  if (bubble) bubble.hidden = name === "Puzzle" ? true : bubble.hidden;
}

export function renderMetaPanel(meta) {
  document.getElementById("metaBeute").textContent = meta.meta_beute;
  const shop = document.getElementById("metaShop");
  shop.innerHTML = "";
  (meta.catalog || []).forEach((item) => {
    const level = meta.upgrades?.[item.id] || 0;
    const maxed = level >= item.max_level;
    const card = document.createElement("div");
    card.className = "meta-card";
    card.innerHTML = `
      <strong>${item.name}</strong>
      <span>Lv ${level}/${item.max_level}</span>
      <p>${item.description}</p>
      <button type="button" class="btn btn-small" ${maxed ? "disabled" : ""}>${item.cost} Meta</button>
    `;
    if (!maxed) {
      card.querySelector("button").addEventListener("click", async () => {
        try {
          const updated = await import("./api.js").then((m) => m.api.metaBuy(item.id));
          renderMetaPanel({ ...meta, ...updated });
          showToast("Upgrade gekauft!");
        } catch (e) {
          showToast(e.message);
        }
      });
    }
    shop.appendChild(card);
  });
}
