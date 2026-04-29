"""
Parse all PZ recipes from media/scripts/*.txt.

Recipe DSL (verified from inspection of vanilla scripts):
    recipe Recipe Name {
        IngredientA,           # consume 1
        IngredientB=3,         # consume 3
        keep IngredientC,      # tool, not consumed
        Item1/Item2/Item3,     # OR list (any one)

        Result: Module.Item,   # output (Module. prefix optional, defaults to Base)
        Result: Module.Item=2, # output 2 of
        Time: 80.0,
        Category: Survivalist,
        SkillRequired: Carpentry=2,
        NeedToBeLearn: false,
        ...
    }

Output: data/recipes.json — list of records, each:
    {
        name, result_id, result_count,
        time, category, skill_name, skill_level,
        need_to_be_learn,
        ingredients: [
            {name, count, kept, alts: [other names if OR list]}
        ],
        source_file
    }
"""

import json
import re
import sys
from pathlib import Path


RECIPE_RE = re.compile(r"\brecipe\s+([^\{]+?)\s*\{", re.MULTILINE)
MODULE_RE = re.compile(r"\bmodule\s+([A-Za-z0-9_]+)\s*\{", re.MULTILINE)

# Known metadata keys inside a recipe block (anything else is treated as ingredient line)
METADATA_KEYS = {
    "Result", "Time", "Category", "NeedToBeLearn", "SkillRequired",
    "OnTest", "OnGiveXP", "OnCreate", "AnimNode", "IsHidden",
    "Sound", "AllowFrozenItem", "AllowRottenItem", "RemoveResultItem",
    "StopOnRun", "StopOnWalk", "Heat", "NeedHeatCheck", "KeepFood",
    "Prop1", "Prop2", "Override", "OnCanPerform", "Tags", "OverrideRecipe",
}


def find_matching_brace(text, open_idx):
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


def split_qty(token):
    """'Plank=3' -> ('Plank', 3); 'Plank' -> ('Plank', 1)."""
    if "=" in token:
        name, qty = token.split("=", 1)
        try:
            return name.strip(), int(qty.strip())
        except ValueError:
            return name.strip(), 1
    return token.strip(), 1


def parse_ingredient_line(line):
    """
    Parse one ingredient/tool line.
    'keep Hammer'              -> {name: Hammer, count: 1, kept: True, alts: []}
    'Plank=3'                  -> {name: Plank, count: 3, kept: False, alts: []}
    'Twine/RippedSheets'       -> {name: Twine, count: 1, kept: False, alts: [RippedSheets]}
    """
    s = line.strip().rstrip(",").strip()
    kept = False
    if s.startswith("keep "):
        kept = True
        s = s[5:].strip()
    # OR list separated by '/'
    options = [opt.strip() for opt in s.split("/") if opt.strip()]
    if not options:
        return None
    primary, count = split_qty(options[0])
    alts = [split_qty(o)[0] for o in options[1:]]
    return {"name": primary, "count": count, "kept": kept, "alts": alts}


def parse_recipe_body(body, default_module):
    """Parse the inside of `recipe NAME { ... }` block."""
    rec = {
        "name": None, "result_id": "", "result_count": 1,
        "time": None, "category": None,
        "skill_name": None, "skill_level": None,
        "need_to_be_learn": None,
        "ingredients": [],
    }

    for raw in body.split("\n"):
        line = raw.split("/*")[0].split("//")[0].strip()
        if not line or line in {"{", "}"}:
            continue
        line = line.rstrip(",").strip()
        if not line:
            continue

        # Check metadata key:value
        # Use regex that captures KEY (alphanumeric) followed by = or :
        m = re.match(r"^([A-Za-z]\w*)\s*[:=]\s*(.+)$", line)
        if m and m.group(1) in METADATA_KEYS:
            key = m.group(1)
            value = m.group(2).strip()
            if key == "Result":
                # 'Module.Item' or 'Item' (default Base) and optionally '=N'
                name, qty = split_qty(value)
                if "." not in name:
                    name = f"{default_module}.{name}"
                rec["result_id"] = name
                rec["result_count"] = qty
            elif key == "Time":
                try: rec["time"] = float(value)
                except ValueError: pass
            elif key == "Category":
                rec["category"] = value
            elif key == "SkillRequired":
                # 'Carpentry=3' or 'Carpentry=3;Strength=2' (rare, multi-skill)
                first = value.split(";")[0]
                if "=" in first:
                    s, l = first.split("=", 1)
                    rec["skill_name"] = s.strip()
                    try: rec["skill_level"] = int(l.strip())
                    except ValueError: pass
            elif key == "NeedToBeLearn":
                rec["need_to_be_learn"] = value.lower() == "true"
            # Other metadata: ignore for now
            continue

        # Otherwise: ingredient line
        ing = parse_ingredient_line(line)
        if ing:
            rec["ingredients"].append(ing)

    return rec


def parse_file(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    recipes = []

    for m_module in MODULE_RE.finditer(text):
        module_name = m_module.group(1)
        b_open = text.find("{", m_module.end() - 1)
        if b_open < 0: continue
        b_close = find_matching_brace(text, b_open)
        if b_close < 0: continue
        module_body = text[b_open + 1:b_close]

        for m_recipe in RECIPE_RE.finditer(module_body):
            recipe_name = m_recipe.group(1).strip()
            r_open = module_body.find("{", m_recipe.end() - 1)
            if r_open < 0: continue
            r_close = find_matching_brace(module_body, r_open)
            if r_close < 0: continue
            body = module_body[r_open + 1:r_close]
            rec = parse_recipe_body(body, default_module=module_name)
            rec["name"] = recipe_name
            rec["source_file"] = path.name
            if rec["result_id"]:
                recipes.append(rec)

    return recipes


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <scripts_dir> <output_json>")
        sys.exit(1)
    scripts_dir = Path(sys.argv[1])
    out_path = Path(sys.argv[2])

    txt_files = sorted(scripts_dir.rglob("*.txt"))
    print(f"Scanning {len(txt_files)} script files for recipes")

    all_recipes = []
    for p in txt_files:
        try:
            recs = parse_file(p)
            all_recipes.extend(recs)
        except Exception as e:
            print(f"  {p.name}: FAILED -- {e}")

    print(f"Total recipes: {len(all_recipes)}")
    skill_count = sum(1 for r in all_recipes if r["skill_name"])
    print(f"With SkillRequired: {skill_count}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_recipes, f, indent=2, ensure_ascii=False)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
