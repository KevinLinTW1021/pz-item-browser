# PZ Item Browser

A simple static page for searching all Project Zomboid items and copying `/additem` commands for server administration.

**Live page:** _enable GitHub Pages on this repo to get a URL_

## Features

- Browse all 2,283 vanilla items from Build 41
- Inline icons for ~83% of items (extracted from PZ texturepacks)
- Search by name, ID, type, or category
- Filter by item type (Clothing, Food, Weapon, etc.) or display category
- Click any item to copy the `/additem "<player>" Module.Item 1` chat command to your clipboard
- Editable player name field (default: `kdog`)

## Disclaimer

**This is an unofficial, non-commercial fan tool. It is not affiliated with, endorsed by, or sponsored by The Indie Stone Ltd.**

All Project Zomboid item names, icons, and game data shown here are property of The Indie Stone Ltd., reproduced for the sole purpose of helping legitimate server administrators look up item IDs.

**You must own a legitimate copy of Project Zomboid to use this tool meaningfully** — `/additem` is a server admin chat command that only works inside the game.

**Please support the developers** by purchasing the game on [Steam](https://store.steampowered.com/app/108600/Project_Zomboid/).

If The Indie Stone wishes this content to be removed, please open an issue and the repo will be taken down.

---

此為非官方社群工具，與 The Indie Stone 無關聯。所有物品圖示、名稱、資料皆為 The Indie Stone Ltd. 所有，此處僅供伺服器管理員查詢使用。**請支持正版**，到 [Steam](https://store.steampowered.com/app/108600/Project_Zomboid/) 購買 Project Zomboid。

## How it was built

The build pipeline (in `tools/`) does three things:

1. **`extract_packs.py`** — parses Project Zomboid's `.pack` texturepack files and extracts each sub-texture as a standalone PNG. Supports both the old format (page count + raw PNG inline + `0xDEADBEEF` terminator) and the newer `PZPK` format (magic + version + length-prefixed PNG, no terminator).
2. **`parse_items.py`** — walks `media/scripts/*.txt`, parses each `module { item Foo { ... } }` block into a JSON record (display name, full ID, type, category, icon name, weight).
3. **`generate_html.py`** — joins the items list with the icon index, embeds everything inline into a single self-contained `index.html` with vanilla-JS search and filter.

To rebuild from your own PZ install:

```
python tools/extract_packs.py "<PZ install>/media/texturepacks" output/icons
python tools/parse_items.py    "<PZ install>/media/scripts"      data/items.json
python tools/generate_html.py  data/items.json output/icon_index.json output/index.html
```

## License

The build scripts in `tools/` are MIT-licensed (see `LICENSE`).

The icons in `icons/` and item metadata are © The Indie Stone Ltd. and are NOT covered by the MIT license — they are reproduced under fair-use / community-tool conventions for reference only.
