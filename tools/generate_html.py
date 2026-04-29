"""
Generate the single-page item browser HTML.

Inputs:
  data/items.json       (parse_items.py output)
  data/recipes.json     (parse_recipes.py output) — optional
  output/icon_index.json (extract_packs.py output)

Output: <html_path>
"""

import json
from pathlib import Path
import sys


def first(v):
    return v[0] if isinstance(v, list) else v


def main():
    if len(sys.argv) < 5:
        print(f"Usage: {sys.argv[0]} <items.json> <recipes.json> <icon_index.json> <output_html>")
        sys.exit(1)

    items = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    recipes = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    icon_index = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
    out_path = Path(sys.argv[4])

    minimal = []
    for it in items:
        icon_raw = first(it.get("Icon", "")) or ""
        icon_file = icon_index.get(f"Item_{icon_raw}", {}).get("file") if icon_raw else None
        minimal.append({
            "name": it.get("_name", ""),
            "module": it.get("_module", ""),
            "id": it.get("_full_id", ""),
            "display": first(it.get("DisplayName", "")) or it.get("_name", ""),
            "type": first(it.get("Type", "")) or "",
            "cat": first(it.get("DisplayCategory", "")) or "",
            "weight": first(it.get("Weight", "")) or "",
            "icon": icon_file or "",
        })

    types = sorted({m["type"] for m in minimal if m["type"]})
    cats = sorted({m["cat"] for m in minimal if m["cat"]})

    payload = {
        "items": minimal,
        "recipes": recipes,
        "types": types,
        "cats": cats,
    }

    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    html = HTML_TEMPLATE.replace("__PAYLOAD__", payload_json) \
                        .replace("__COUNT__", str(len(minimal)))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"Generated: {out_path}")
    print(f"  items: {len(minimal)}, recipes: {len(recipes)}")
    print(f"  types: {len(types)}, categories: {len(cats)}")
    with_icon = sum(1 for m in minimal if m["icon"])
    print(f"  items with icon: {with_icon} ({100*with_icon//len(minimal)}%)")


HTML_TEMPLATE = r"""<!doctype html>
<html lang="zh-TW">
<head>
<meta charset="utf-8">
<title>PZ Item Browser</title>
<style>
  :root {
    --bg: #1a1815;
    --panel: #25221e;
    --panel2: #2e2a25;
    --border: #3a352e;
    --text: #e8dfd0;
    --dim: #8a8275;
    --accent: #c9a25b;
    --hit: #4a3f2c;
    --good: #6b9a4a;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--text);
    font-family: -apple-system, "Segoe UI", "Microsoft JhengHei", sans-serif;
    font-size: 13px;
  }
  header {
    position: sticky; top: 0; z-index: 10;
    background: var(--panel); border-bottom: 1px solid var(--border);
    padding: 10px 14px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center;
  }
  header h1 { margin: 0; font-size: 16px; color: var(--accent); }
  header .stat { color: var(--dim); margin-left: auto; }
  input[type=search], select, input.player {
    background: #1a1815; color: var(--text); border: 1px solid var(--border);
    padding: 6px 10px; border-radius: 4px; font: inherit;
  }
  input[type=search] { min-width: 280px; }
  .checkbox-label {
    display: inline-flex; align-items: center; gap: 6px;
    color: var(--text); cursor: pointer;
    background: #1a1815; padding: 6px 10px; border-radius: 4px;
    border: 1px solid var(--border); user-select: none;
  }
  .checkbox-label:hover { border-color: var(--accent); }
  .checkbox-label input { margin: 0; cursor: pointer; }
  .player-name {
    background: #1a1815; padding: 6px 10px; border-radius: 4px;
    border: 1px solid var(--border); color: var(--accent);
  }
  .player-name input {
    background: transparent; border: none; color: var(--accent);
    font: inherit; width: 120px; outline: none;
  }
  #grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 8px; padding: 12px;
  }
  .card {
    background: var(--panel); border: 1px solid var(--border); border-radius: 4px;
    padding: 8px; display: flex; gap: 10px; align-items: center;
    cursor: pointer; transition: background .1s;
    position: relative;
  }
  .card:hover { background: var(--hit); border-color: var(--accent); }
  .card.has-recipe::after {
    content: ""; position: absolute; top: 4px; right: 4px;
    width: 6px; height: 6px; border-radius: 50%; background: var(--good);
  }
  .icon-wrap {
    width: 48px; height: 48px; flex-shrink: 0;
    background: #14110e; border: 1px solid #2a2620; border-radius: 3px;
    display: flex; align-items: center; justify-content: center;
    image-rendering: pixelated;
  }
  .icon-wrap img { max-width: 44px; max-height: 44px; }
  .icon-wrap.empty { color: #4a443a; font-size: 10px; }
  .icon-wrap.small { width: 28px; height: 28px; }
  .icon-wrap.small img { max-width: 24px; max-height: 24px; }
  .meta { flex: 1; min-width: 0; }
  .meta .name { font-weight: bold; margin-bottom: 2px;
                white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .meta .id { color: var(--dim); font-family: monospace; font-size: 11px;
              white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .meta .tags { font-size: 11px; color: #a89878; margin-top: 2px; }
  .meta .tags span { background: #1a1815; padding: 1px 5px; border-radius: 2px;
                     margin-right: 4px; border: 1px solid var(--border); }
  #empty { padding: 40px; text-align: center; color: var(--dim); display: none; }
  footer { padding: 16px 24px 32px; color: var(--dim); font-size: 12px; text-align: center; line-height: 1.5; }
  footer .disclaimer p { margin: 6px auto; max-width: 720px; }
  footer a { color: var(--accent); }

  /* Toast */
  #toast {
    position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
    background: var(--accent); color: #1a1815; padding: 10px 20px; border-radius: 4px;
    font-weight: bold; opacity: 0; transition: opacity .2s; pointer-events: none;
    z-index: 100;
  }
  #toast.show { opacity: 1; }

  /* Modal */
  #backdrop {
    position: fixed; inset: 0; background: rgba(0,0,0,.6);
    display: none; align-items: center; justify-content: center;
    z-index: 50; padding: 20px;
  }
  #backdrop.open { display: flex; }
  #modal {
    background: var(--panel); border: 1px solid var(--border); border-radius: 6px;
    width: 100%; max-width: 720px; max-height: 90vh; overflow: auto;
    padding: 0; box-shadow: 0 10px 30px rgba(0,0,0,.5);
  }
  #modal .modal-head {
    display: flex; gap: 14px; padding: 16px; border-bottom: 1px solid var(--border);
    align-items: center;
  }
  #modal .modal-head .icon-wrap { width: 64px; height: 64px; }
  #modal .modal-head .icon-wrap img { max-width: 60px; max-height: 60px; }
  #modal .modal-head .info { flex: 1; min-width: 0; }
  #modal .modal-head h2 { margin: 0 0 4px; font-size: 18px; color: var(--accent); }
  #modal .modal-head .id { color: var(--dim); font-family: monospace; font-size: 12px; }
  #modal .modal-head .stats { font-size: 12px; color: #a89878; margin-top: 4px; }
  #modal .close {
    cursor: pointer; padding: 6px 10px; border-radius: 3px;
    background: var(--panel2); border: 1px solid var(--border); color: var(--text);
  }
  #modal .close:hover { background: var(--hit); }
  #modal .actions {
    padding: 12px 16px; border-bottom: 1px solid var(--border);
    display: flex; gap: 8px; flex-wrap: wrap;
  }
  #modal .actions button {
    padding: 8px 14px; border-radius: 4px; border: 1px solid var(--accent);
    background: var(--accent); color: #1a1815; font: inherit; font-weight: bold;
    cursor: pointer;
  }
  #modal .actions button.secondary {
    background: var(--panel2); color: var(--text); border-color: var(--border);
    font-weight: normal;
  }
  #modal .actions button:hover { filter: brightness(1.1); }
  #modal .recipes {
    padding: 14px 16px;
  }
  #modal .recipes h3 {
    margin: 0 0 8px; font-size: 13px; color: var(--accent);
    text-transform: uppercase; letter-spacing: 1px;
  }
  #modal .recipe {
    background: #1f1c19; border: 1px solid var(--border);
    border-radius: 4px; padding: 10px; margin-bottom: 8px;
  }
  #modal .recipe .rname { font-weight: bold; margin-bottom: 4px; }
  #modal .recipe .rmeta { font-size: 11px; color: var(--dim); margin-bottom: 8px; }
  #modal .recipe .rmeta span { margin-right: 12px; }
  #modal .ingredients { display: flex; flex-direction: column; gap: 4px; }
  #modal .ingredient { display: flex; align-items: center; gap: 8px; padding: 4px; }
  #modal .ingredient.kept { opacity: 0.85; }
  #modal .ingredient .ing-name { flex: 1; }
  #modal .ingredient .ing-qty {
    background: var(--bg); padding: 2px 8px; border-radius: 3px;
    font-family: monospace; color: var(--accent);
  }
  #modal .ingredient .alts { color: var(--dim); font-size: 11px; }
  #modal .ingredient.tool .ing-qty { background: transparent; color: #6a8a4a; }
  #modal .clickable { cursor: pointer; color: var(--text); border-bottom: 1px dotted var(--dim); }
  #modal .clickable:hover { color: var(--accent); border-bottom-color: var(--accent); }
  #modal .no-recipes {
    padding: 20px; text-align: center; color: var(--dim);
    font-style: italic;
  }
</style>
</head>
<body>
<header>
  <h1>PZ Item Browser</h1>
  <input id="search" type="search" placeholder="Search name / id / category...">
  <select id="filter-type"><option value="">All types</option></select>
  <select id="filter-cat"><option value="">All categories</option></select>
  <label class="checkbox-label"><input id="filter-craftable" type="checkbox"> Craftable only</label>
  <span class="player-name">Player: <input id="playername" class="player" value="kdog"></span>
  <span class="stat" id="stat">__COUNT__ items</span>
</header>
<div id="grid"></div>
<div id="empty">No items match.</div>
<footer>
  <p>Click any item to see details &amp; recipes. Use <strong>Copy /additem</strong> in the modal to copy the admin spawn command.</p>
  <p style="font-size: 11px; opacity: 0.7;">Items with a green dot have a known recipe in the vanilla scripts.</p>
  <hr style="border-color: var(--border); margin: 12px auto; max-width: 800px;">
  <div class="disclaimer">
    <p><strong>This is an unofficial community / admin tool. Not affiliated with The Indie Stone Ltd.</strong></p>
    <p>
      All item names, icons, and game data are property of
      <a href="https://projectzomboid.com" target="_blank" rel="noopener">The Indie Stone Ltd.</a>
      &mdash; reproduced here for reference and server administration.
      You must own Project Zomboid for this tool to be useful.
    </p>
    <p>
      <strong>Please support the developers</strong>:
      <a href="https://store.steampowered.com/app/108600/Project_Zomboid/" target="_blank" rel="noopener">
        Buy Project Zomboid on Steam
      </a>
    </p>
    <p style="margin-top: 12px; font-size: 11px;">
      &mdash;&nbsp;&nbsp;
      此為非官方社群／伺服器管理員工具，與 The Indie Stone 無關聯。
      所有物品名稱、圖示、遊戲資料皆為 The Indie Stone Ltd. 所有，
      此處僅供管理員查詢使用。請支持正版，到
      <a href="https://store.steampowered.com/app/108600/Project_Zomboid/" target="_blank" rel="noopener">Steam</a>
      購買 Project Zomboid 支持開發團隊。
    </p>
  </div>
</footer>

<div id="toast"></div>

<div id="backdrop"></div>

<script>
const PAYLOAD = __PAYLOAD__;
const ITEMS = PAYLOAD.items;
const RECIPES = PAYLOAD.recipes;
const TYPES = PAYLOAD.types;
const CATS = PAYLOAD.cats;

// Build lookup maps
const ITEM_BY_NAME = new Map();   // bare name (no module) -> item
const ITEM_BY_ID = new Map();     // Module.Name -> item
for (const it of ITEMS) {
  ITEM_BY_NAME.set(it.name, it);
  ITEM_BY_ID.set(it.id, it);
}

// Recipes that produce a given item id
const RECIPES_BY_RESULT = new Map();
for (const r of RECIPES) {
  if (!r.result_id) continue;
  if (!RECIPES_BY_RESULT.has(r.result_id)) RECIPES_BY_RESULT.set(r.result_id, []);
  RECIPES_BY_RESULT.get(r.result_id).push(r);
}

const $ = (s) => document.querySelector(s);
const grid = $("#grid");
const search = $("#search");
const filterType = $("#filter-type");
const filterCat = $("#filter-cat");
const filterCraftable = $("#filter-craftable");
const stat = $("#stat");
const empty = $("#empty");
const toast = $("#toast");
const backdrop = $("#backdrop");
const playerInput = $("#playername");

for (const t of TYPES) { const o = document.createElement("option"); o.value = t; o.textContent = t; filterType.appendChild(o); }
for (const c of CATS) { const o = document.createElement("option"); o.value = c; o.textContent = c; filterCat.appendChild(o); }

function showToast(msg) {
  toast.textContent = msg;
  toast.classList.add("show");
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => toast.classList.remove("show"), 1400);
}

function copyToClipboard(text) {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).catch(() => fallbackCopy(text));
  } else {
    fallbackCopy(text);
  }
}
function fallbackCopy(text) {
  const ta = document.createElement("textarea");
  ta.value = text; document.body.appendChild(ta);
  ta.select(); document.execCommand("copy"); ta.remove();
}

function findIngredientItem(rawName) {
  // ingredient names in PZ recipes are usually bare (no module). Could also be Base.X.
  if (rawName.indexOf(".") >= 0) {
    return ITEM_BY_ID.get(rawName);
  }
  return ITEM_BY_NAME.get(rawName);
}

function renderIcon(itemOrIconFile, small=false) {
  const wrap = document.createElement("div");
  wrap.className = "icon-wrap" + (small ? " small" : "");
  let iconFile = "";
  if (typeof itemOrIconFile === "string") iconFile = itemOrIconFile;
  else if (itemOrIconFile) iconFile = itemOrIconFile.icon || "";
  if (iconFile) {
    const img = document.createElement("img");
    img.src = "icons/" + iconFile;
    img.loading = "lazy";
    img.onerror = () => { wrap.classList.add("empty"); wrap.textContent = "?"; img.remove(); };
    wrap.appendChild(img);
  } else {
    wrap.classList.add("empty");
    wrap.textContent = small ? "?" : "no img";
  }
  return wrap;
}

function makeCard(item) {
  const card = document.createElement("div");
  card.className = "card";
  card.title = item.id;
  if (RECIPES_BY_RESULT.has(item.id)) card.classList.add("has-recipe");

  card.appendChild(renderIcon(item));

  const meta = document.createElement("div");
  meta.className = "meta";
  const name = document.createElement("div");
  name.className = "name"; name.textContent = item.display || item.name;
  const id = document.createElement("div");
  id.className = "id"; id.textContent = item.id;
  const tags = document.createElement("div");
  tags.className = "tags";
  if (item.type) { const s = document.createElement("span"); s.textContent = item.type; tags.appendChild(s); }
  if (item.cat) { const s = document.createElement("span"); s.textContent = item.cat; tags.appendChild(s); }
  meta.appendChild(name); meta.appendChild(id); meta.appendChild(tags);

  card.appendChild(meta);
  card.addEventListener("click", () => openModal(item));
  return card;
}

function buildIngredientRow(ing) {
  const row = document.createElement("div");
  row.className = "ingredient" + (ing.kept ? " tool kept" : "");

  const ingItem = findIngredientItem(ing.name);
  row.appendChild(renderIcon(ingItem, true));

  const nameEl = document.createElement("span");
  nameEl.className = "ing-name";
  if (ingItem) {
    const a = document.createElement("span");
    a.className = "clickable";
    a.textContent = ingItem.display || ing.name;
    a.addEventListener("click", (e) => { e.stopPropagation(); openModal(ingItem); });
    nameEl.appendChild(a);
  } else {
    nameEl.textContent = ing.name;
  }
  if (ing.alts && ing.alts.length) {
    const alts = document.createElement("span");
    alts.className = "alts";
    alts.textContent = "  or " + ing.alts.map(a => {
      const it = findIngredientItem(a);
      return it ? (it.display || a) : a;
    }).join(" / ");
    nameEl.appendChild(alts);
  }
  row.appendChild(nameEl);

  const qty = document.createElement("span");
  qty.className = "ing-qty";
  qty.textContent = ing.kept ? "tool" : ("× " + ing.count);
  row.appendChild(qty);

  return row;
}

function buildRecipeBlock(rec) {
  const box = document.createElement("div");
  box.className = "recipe";
  const name = document.createElement("div");
  name.className = "rname";
  name.textContent = rec.name;
  box.appendChild(name);

  const meta = document.createElement("div");
  meta.className = "rmeta";
  const bits = [];
  if (rec.time != null) bits.push(`<span>Time: ${rec.time}</span>`);
  if (rec.category) bits.push(`<span>Category: ${rec.category}</span>`);
  if (rec.skill_name) bits.push(`<span>Skill: ${rec.skill_name} ${rec.skill_level || 0}</span>`);
  if (rec.need_to_be_learn) bits.push(`<span>Recipe must be learned</span>`);
  if (rec.result_count > 1) bits.push(`<span>Yields × ${rec.result_count}</span>`);
  meta.innerHTML = bits.join("");
  box.appendChild(meta);

  const ings = document.createElement("div");
  ings.className = "ingredients";
  for (const i of rec.ingredients) ings.appendChild(buildIngredientRow(i));
  box.appendChild(ings);
  return box;
}

function openModal(item) {
  backdrop.innerHTML = "";

  const modal = document.createElement("div");
  modal.id = "modal";

  // Head
  const head = document.createElement("div");
  head.className = "modal-head";
  head.appendChild(renderIcon(item));
  const info = document.createElement("div");
  info.className = "info";
  const h2 = document.createElement("h2"); h2.textContent = item.display || item.name; info.appendChild(h2);
  const idEl = document.createElement("div"); idEl.className = "id"; idEl.textContent = item.id; info.appendChild(idEl);
  const stats = document.createElement("div");
  stats.className = "stats";
  const sBits = [];
  if (item.type) sBits.push(item.type);
  if (item.cat) sBits.push(item.cat);
  if (item.weight) sBits.push("Weight: " + item.weight);
  stats.textContent = sBits.join("  ·  ");
  info.appendChild(stats);
  head.appendChild(info);
  const closeBtn = document.createElement("button"); closeBtn.className = "close"; closeBtn.textContent = "✕ Close";
  closeBtn.addEventListener("click", closeModal);
  head.appendChild(closeBtn);
  modal.appendChild(head);

  // Actions
  const actions = document.createElement("div");
  actions.className = "actions";
  const copyBtn = document.createElement("button");
  copyBtn.textContent = "Copy /additem command";
  copyBtn.addEventListener("click", () => {
    const player = playerInput.value.trim() || "kdog";
    const cmd = `/additem "${player}" ${item.id} 1`;
    copyToClipboard(cmd);
    showToast("Copied: " + cmd);
  });
  actions.appendChild(copyBtn);
  modal.appendChild(actions);

  // Recipes
  const wrap = document.createElement("div");
  wrap.className = "recipes";
  const recipesForItem = RECIPES_BY_RESULT.get(item.id) || [];
  if (recipesForItem.length) {
    const h3 = document.createElement("h3");
    h3.textContent = `How to craft  (${recipesForItem.length} recipe${recipesForItem.length>1?"s":""})`;
    wrap.appendChild(h3);
    for (const r of recipesForItem) wrap.appendChild(buildRecipeBlock(r));
  } else {
    const none = document.createElement("div");
    none.className = "no-recipes";
    none.textContent = "No recipe found in vanilla scripts. Use the /additem command above to spawn directly.";
    wrap.appendChild(none);
  }
  modal.appendChild(wrap);

  backdrop.appendChild(modal);
  backdrop.classList.add("open");
}

function closeModal() {
  backdrop.classList.remove("open");
  backdrop.innerHTML = "";
}

backdrop.addEventListener("click", (e) => {
  if (e.target === backdrop) closeModal();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeModal();
});

// Render grid
function render() {
  const q = search.value.trim().toLowerCase();
  const tFilt = filterType.value;
  const cFilt = filterCat.value;
  const onlyCraftable = filterCraftable.checked;
  const filtered = ITEMS.filter((it) => {
    if (tFilt && it.type !== tFilt) return false;
    if (cFilt && it.cat !== cFilt) return false;
    if (onlyCraftable && !RECIPES_BY_RESULT.has(it.id)) return false;
    if (q) {
      const hay = (it.name + " " + it.display + " " + it.id + " " + it.type + " " + it.cat).toLowerCase();
      if (hay.indexOf(q) < 0) return false;
    }
    return true;
  });
  grid.innerHTML = "";
  const frag = document.createDocumentFragment();
  for (const it of filtered) frag.appendChild(makeCard(it));
  grid.appendChild(frag);
  stat.textContent = `${filtered.length} / ${ITEMS.length} items`;
  empty.style.display = filtered.length === 0 ? "block" : "none";
}

let renderTimer = null;
search.addEventListener("input", () => {
  clearTimeout(renderTimer);
  renderTimer = setTimeout(render, 80);
});
filterType.addEventListener("change", render);
filterCat.addEventListener("change", render);
filterCraftable.addEventListener("change", render);

render();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
