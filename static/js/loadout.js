import { showToast } from "./hud.js";

const ITEM_ICONS = {
  dreihaus_vampir: "3",
  reihen_rakete: "🚀",
  neon_sieben: "7",
  combo_kaffee: "☕",
  block_boss: "▦",
  waschbaers_tasche: "🎒",
  waschbaer_ablenkung: "🦝",
  gerade_gier: "⇈",
  raccoon_luck: "🍀",
  chaos_nachbar: "⁂",
  ticket_magnet: "🧲",
  schnellschreiber: "⚡",
  schummel_zettel: "📝",
  radiergummi: "🧽",
  beute_boost: "💰",
  herz_pflaster: "💗",
  fifty_fifty: "½",
  reveal: "👁",
  extra_moves: "+5",
};

const KNIFF_LABELS = {
  schummel_zettel: { name: "Schummel-Zettel", description: "Füllt eine zufällige leere Zelle korrekt." },
  radiergummi: { name: "Radiergummi Deluxe", description: "Entfernt eine falsche Zelle ohne Herzverlust." },
  beute_boost: { name: "Beute-Boost", description: "+30 sofortige Punkte." },
  herz_pflaster: { name: "Herz-Pflaster", description: "Stellt 1 Herz wieder her." },
};

export function itemIcon(id) {
  return ITEM_ICONS[id] || "◆";
}

export function itemTooltip(name, description) {
  return `${name} — ${description}`;
}

export function kniffMeta(id) {
  return KNIFF_LABELS[id] || {
    name: id.replace(/_/g, " "),
    description: "Verbrauchs-Kniff",
  };
}

export function createLoadoutChip({
  tag = "span",
  icon,
  label,
  title,
  badge = null,
  className = "loadout-chip",
  disabled = false,
  onActivate = null,
  showHintOnTap = false,
}) {
  const el = document.createElement(tag);
  el.className = className;
  if (disabled) {
    el.classList.add("disabled");
    el.setAttribute("aria-disabled", "true");
  }
  el.title = title;
  el.setAttribute("aria-label", label);

  const iconEl = document.createElement("span");
  iconEl.className = "loadout-icon";
  iconEl.setAttribute("aria-hidden", "true");
  iconEl.textContent = icon;
  el.appendChild(iconEl);

  if (badge != null) {
    const badgeEl = document.createElement("span");
    badgeEl.className = "loadout-badge";
    badgeEl.textContent = badge;
    el.appendChild(badgeEl);
  }

  if (tag === "button") {
    el.type = "button";
    if (disabled) el.disabled = true;
  }

  const hint = () => showToast(title, 2400);

  if (onActivate) {
    el.addEventListener("click", () => {
      if (disabled) {
        hint();
        return;
      }
      onActivate();
    });
  } else if (showHintOnTap) {
    el.addEventListener("click", hint);
  }

  return el;
}
