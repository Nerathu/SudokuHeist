import { api } from "./api.js";
import { showToast } from "./hud.js";

export function renderMap(state) {
  const track = document.getElementById("mapTrack");
  track.innerHTML = "";
  state.map_nodes.forEach((node, i) => {
    const el = document.createElement("div");
    el.className = "map-node";
    if (i < state.map_index) el.classList.add("done");
    if (i === state.map_index) el.classList.add("current");
    if (node.type === "boss") el.classList.add("boss");
    if (node.type === "shop") el.classList.add("shop");
    el.innerHTML = `<span class="node-type">${node.type}</span><strong>${node.label}</strong>`;
    track.appendChild(el);
  });
}

export function renderShop(state) {
  document.getElementById("shopBeute").textContent = state.beute;
  renderOffers("shopTricks", state.shop.tricks, "trick", state);
  renderOffers("shopKniffs", state.shop.kniffs, "kniff", state);
  const rerollBtn = document.getElementById("btnShopReroll");
  const canReroll = state.beute >= state.shop.reroll_cost;
  rerollBtn.textContent = `Reroll (${state.shop.reroll_cost})`;
  rerollBtn.disabled = !canReroll;
  rerollBtn.classList.toggle("btn-unaffordable", !canReroll);
}

function renderOffers(containerId, items, kind, state) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";
  const ownedTricks = new Set(state.trick_ids || []);
  const visible =
    kind === "trick" ? items.filter((item) => !ownedTricks.has(item.id)) : items;

  if (!visible.length) {
    const empty = document.createElement("p");
    empty.className = "shop-empty";
    empty.textContent =
      kind === "trick" ? "Alle Tricks für diesen Run schon dabei." : "Keine Angebote.";
    container.appendChild(empty);
    return;
  }

  visible.forEach((item) => {
    const canAfford = state.beute >= item.cost;
    const card = document.createElement("button");
    card.type = "button";
    card.className = "shop-card";
    if (!canAfford) card.classList.add("unaffordable");
    card.disabled = !canAfford;
    card.innerHTML = `
      <strong>${item.name}</strong>
      <p>${item.description}</p>
      <span class="cost">${item.cost} Beute</span>
    `;
    card.addEventListener("click", async () => {
      if (!canAfford) return;
      try {
        const updated = await api.shopBuy(item.id, kind);
        if (window.__sudokuHeistUpdate) window.__sudokuHeistUpdate(updated);
        showToast(`${item.name} gekauft!`);
      } catch (e) {
        showToast(e.message);
      }
    });
    container.appendChild(card);
  });
}
