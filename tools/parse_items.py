"""
Parse all PZ item definitions from media/scripts/*.txt.

Each .txt has:
    module ModuleName {
        item ItemName {
            DisplayName = ...,
            Type = ...,
            Icon = ...,
            ...
        }
        ...
    }

Recipes, models, sounds etc also live in modules but use different prefixes.
We collect only `item NAME { ... }` blocks.

Output: data/items.json
"""

import json
import re
import sys
from pathlib import Path


ITEM_RE = re.compile(r"\bitem\s+([A-Za-z0-9_]+)\s*\{", re.MULTILINE)
MODULE_RE = re.compile(r"\bmodule\s+([A-Za-z0-9_]+)\s*\{", re.MULTILINE)


def find_matching_brace(text, open_idx):
    """Given index of '{', return index of matching '}'."""
    depth = 0
    i = open_idx
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def parse_kv_block(block):
    """Parse 'Key = Value,' lines into a dict. Multiple same-key lines become a list."""
    out = {}
    for line in block.split("\n"):
        line = line.split("/*")[0].split("//")[0].strip()
        if not line or line.startswith("/"):
            continue
        line = line.rstrip(",").strip()
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        if not k:
            continue
        if k in out:
            if isinstance(out[k], list):
                out[k].append(v)
            else:
                out[k] = [out[k], v]
        else:
            out[k] = v
    return out


def parse_file(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    items = []

    # Find all module blocks
    for m_module in MODULE_RE.finditer(text):
        module_name = m_module.group(1)
        brace_open = text.find("{", m_module.end() - 1)
        if brace_open < 0:
            continue
        brace_close = find_matching_brace(text, brace_open)
        if brace_close < 0:
            continue
        module_body = text[brace_open + 1:brace_close]

        # Find items within this module
        for m_item in ITEM_RE.finditer(module_body):
            item_name = m_item.group(1)
            i_open = module_body.find("{", m_item.end() - 1)
            if i_open < 0:
                continue
            i_close = find_matching_brace(module_body, i_open)
            if i_close < 0:
                continue
            item_body = module_body[i_open + 1:i_close]
            kv = parse_kv_block(item_body)
            kv["_name"] = item_name
            kv["_module"] = module_name
            kv["_full_id"] = f"{module_name}.{item_name}"
            kv["_source_file"] = path.name
            items.append(kv)

    return items


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <scripts_dir> <output_json>")
        sys.exit(1)
    scripts_dir = Path(sys.argv[1])
    out_path = Path(sys.argv[2])

    txt_files = sorted(scripts_dir.rglob("*.txt"))
    print(f"Scanning {len(txt_files)} script files in {scripts_dir}")

    all_items = []
    for p in txt_files:
        try:
            items = parse_file(p)
            all_items.extend(items)
        except Exception as e:
            print(f"  {p.name}: FAILED -- {e}")

    print(f"Total items parsed: {len(all_items)}")

    # Quick stats (some keys appear twice in scripts -> list value, take first)
    def first(v):
        return v[0] if isinstance(v, list) else v

    cats = {}
    types = {}
    with_icon = 0
    for it in all_items:
        c = first(it.get("DisplayCategory", "?"))
        cats[c] = cats.get(c, 0) + 1
        t = first(it.get("Type", "?"))
        types[t] = types.get(t, 0) + 1
        if it.get("Icon"):
            with_icon += 1
    print(f"With Icon=: {with_icon}")
    print(f"Top types: {sorted(types.items(), key=lambda x: -x[1])[:8]}")
    print(f"Top categories: {sorted(cats.items(), key=lambda x: -x[1])[:8]}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, indent=2, ensure_ascii=False)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
