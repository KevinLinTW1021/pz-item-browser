"""
Generate a single-page HTML browser for PZ items.

Inputs:
  data/items.json  (from parse_items.py)
  output/icon_index.json  (from extract_packs.py)
  output/icons/*.png  (icons to reference)

Output:
  output/index.html  (single self-contained page; reads icons from ./icons/)
"""

import json
from pathlib import Path
import sys


def first(v):
    return v[0] if isinstance(v, list) else v


def main():
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <items.json> <icon_index.json> <output_html>")
        sys.exit(1)

    items_path = Path(sys.argv[1])
    icon_index_path = Path(sys.argv[2])
    out_path = Path(sys.argv[3])

    items = json.loads(items_path.read_text(encoding="utf-8"))
    icon_index = json.loads(icon_index_path.read_text(encoding="utf-8"))

    # Build a normalized item list for the page.
    minimal = []
    for it in items:
        icon_raw = first(it.get("Icon", "")) or ""
        icon_key = f"Item_{icon_raw}"
        icon_file = icon_index.get(icon_key, {}).get("file") if icon_raw else None
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

    # All distinct types and categories for dropdowns
    types = sorted({m["type"] for m in minimal if m["type"]})
    cats = sorted({m["cat"] for m in minimal if m["cat"]})

    items_json = json.dumps(minimal, ensure_ascii=False, separators=(",", ":"))
    types_json = json.dumps(types)
    cats_json = json.dumps(cats)

    html = HTML_TEMPLATE.replace("__ITEMS__", items_json) \
                        .replace("__TYPES__", types_json) \
                        .replace("__CATS__", cats_json) \
                        .replace("__COUNT__", str(len(minimal)))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"Generated: {out_path}")
    print(f"  items: {len(minimal)}")
    print(f"  types: {len(types)}")
    print(f"  categories: {len(cats)}")
    with_icon = sum(1 for m in minimal if m["icon"])
    print(f"  with icon: {with_icon} ({100*with_icon//len(minimal)}%)")


HTML_TEMPLATE = r"""<!doctype html>
<html lang="zh-TW">
<head>
<meta charset="utf-8">
<title>PZ Item Browser</title>
<style>
  :root {
    --bg: #1a1815;
    --panel: #25221e;
    --border: #3a352e;
    --text: #e8dfd0;
    --dim: #8a8275;
    --accent: #c9a25b;
    --hit: #4a3f2c;
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
  input[type=search], select {
    background: #1a1815; color: var(--text); border: 1px solid var(--border);
    padding: 6px 10px; border-radius: 4px; font: inherit;
  }
  input[type=search] { min-width: 280px; }
  #grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 8px; padding: 12px;
  }
  .card {
    background: var(--panel); border: 1px solid var(--border); border-radius: 4px;
    padding: 8px; display: flex; gap: 10px; align-items: center;
    cursor: pointer; transition: background .1s;
  }
  .card:hover { background: var(--hit); border-color: var(--accent); }
  .card.copied { background: #2a4a2a; border-color: #4a8a4a; }
  .icon-wrap {
    width: 48px; height: 48px; flex-shrink: 0;
    background: #14110e; border: 1px solid #2a2620; border-radius: 3px;
    display: flex; align-items: center; justify-content: center;
    image-rendering: pixelated;
  }
  .icon-wrap img { max-width: 44px; max-height: 44px; }
  .icon-wrap.empty { color: #4a443a; font-size: 10px; }
  .meta { flex: 1; min-width: 0; }
  .meta .name { font-weight: bold; color: var(--text); margin-bottom: 2px;
                white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .meta .id { color: var(--dim); font-family: monospace; font-size: 11px;
              white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .meta .tags { font-size: 11px; color: #a89878; margin-top: 2px; }
  .meta .tags span { background: #1a1815; padding: 1px 5px; border-radius: 2px;
                     margin-right: 4px; border: 1px solid var(--border); }
  #empty { padding: 40px; text-align: center; color: var(--dim); display: none; }
  #toast {
    position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
    background: var(--accent); color: #1a1815; padding: 10px 20px; border-radius: 4px;
    font-weight: bold; opacity: 0; transition: opacity .2s; pointer-events: none;
  }
  #toast.show { opacity: 1; }
  .player-name {
    background: #1a1815; padding: 6px 10px; border-radius: 4px;
    border: 1px solid var(--border); color: var(--accent);
  }
  .player-name input {
    background: transparent; border: none; color: var(--accent);
    font: inherit; width: 120px; outline: none;
  }
  footer { padding: 16px 24px 32px; color: var(--dim); font-size: 12px; text-align: center; line-height: 1.5; }
  footer .disclaimer p { margin: 6px auto; max-width: 720px; }
  footer a { color: var(--accent); }
</style>
</head>
<body>
<header>
  <h1>PZ Item Browser</h1>
  <input id="search" type="search" placeholder="Search name / id / category...">
  <select id="filter-type"><option value="">All types</option></select>
  <select id="filter-cat"><option value="">All categories</option></select>
  <span class="player-name">Player: <input id="playername" value="kdog"></span>
  <span class="stat" id="stat">__COUNT__ items</span>
</header>
<div id="grid"></div>
<div id="empty">No items match.</div>
<footer>
  <p>Click a card to copy <code>/additem &quot;name&quot; Module.Item 1</code> to clipboard.</p>
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

<script>
const ITEMS = __ITEMS__;
const TYPES = __TYPES__;
const CATS = __CATS__;

const $ = (s) => document.querySelector(s);
const grid = $("#grid");
const search = $("#search");
const filterType = $("#filter-type");
const filterCat = $("#filter-cat");
const stat = $("#stat");
const empty = $("#empty");
const toast = $("#toast");
const playerNameInput = $("#playername");

for (const t of TYPES) {
  const o = document.createElement("option");
  o.value = t; o.textContent = t;
  filterType.appendChild(o);
}
for (const c of CATS) {
  const o = document.createElement("option");
  o.value = c; o.textContent = c;
  filterCat.appendChild(o);
}

function showToast(msg) {
  toast.textContent = msg;
  toast.classList.add("show");
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => toast.classList.remove("show"), 1400);
}

function copyAddItem(card, item) {
  const playerName = playerNameInput.value.trim() || "kdog";
  const cmd = `/additem "${playerName}" ${item.id} 1`;
  navigator.clipboard.writeText(cmd).then(() => {
    showToast("Copied: " + cmd);
    card.classList.add("copied");
    setTimeout(() => card.classList.remove("copied"), 800);
  }, () => {
    // Fallback for non-https
    const ta = document.createElement("textarea");
    ta.value = cmd; document.body.appendChild(ta);
    ta.select(); document.execCommand("copy"); ta.remove();
    showToast("Copied: " + cmd);
  });
}

function makeCard(item) {
  const card = document.createElement("div");
  card.className = "card";
  card.title = item.id;

  const iconWrap = document.createElement("div");
  iconWrap.className = "icon-wrap";
  if (item.icon) {
    const img = document.createElement("img");
    img.src = "icons/" + item.icon;
    img.loading = "lazy";
    img.onerror = () => { iconWrap.classList.add("empty"); iconWrap.textContent = "?"; img.remove(); };
    iconWrap.appendChild(img);
  } else {
    iconWrap.classList.add("empty");
    iconWrap.textContent = "no img";
  }

  const meta = document.createElement("div");
  meta.className = "meta";
  const name = document.createElement("div");
  name.className = "name"; name.textContent = item.display || item.name;
  const id = document.createElement("div");
  id.className = "id"; id.textContent = item.id;
  const tags = document.createElement("div");
  tags.className = "tags";
  if (item.type) {
    const s = document.createElement("span"); s.textContent = item.type; tags.appendChild(s);
  }
  if (item.cat) {
    const s = document.createElement("span"); s.textContent = item.cat; tags.appendChild(s);
  }
  meta.appendChild(name); meta.appendChild(id); meta.appendChild(tags);

  card.appendChild(iconWrap); card.appendChild(meta);
  card.addEventListener("click", () => copyAddItem(card, item));
  return card;
}

let currentItems = [];

function render() {
  const q = search.value.trim().toLowerCase();
  const tFilt = filterType.value;
  const cFilt = filterCat.value;

  const filtered = ITEMS.filter((it) => {
    if (tFilt && it.type !== tFilt) return false;
    if (cFilt && it.cat !== cFilt) return false;
    if (q) {
      const hay = (it.name + " " + it.display + " " + it.id + " " + it.type + " " + it.cat).toLowerCase();
      if (hay.indexOf(q) < 0) return false;
    }
    return true;
  });

  // Re-render only if changed length OR first call. For simplicity always re-render.
  grid.innerHTML = "";
  const frag = document.createDocumentFragment();
  for (const it of filtered) frag.appendChild(makeCard(it));
  grid.appendChild(frag);
  stat.textContent = `${filtered.length} / ${ITEMS.length} items`;
  empty.style.display = filtered.length === 0 ? "block" : "none";
  currentItems = filtered;
}

let renderTimer = null;
function debouncedRender() {
  clearTimeout(renderTimer);
  renderTimer = setTimeout(render, 80);
}

search.addEventListener("input", debouncedRender);
filterType.addEventListener("change", render);
filterCat.addEventListener("change", render);

render();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
