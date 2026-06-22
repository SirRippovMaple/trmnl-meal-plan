import json
import re
from datetime import date, datetime
from pathlib import Path


_FILE_RE = re.compile(r"^Meal Plan (\d{4}-\d{2}-\d{2})\.json$")


def find_current_file(base_dir: str, today: date) -> Path | None:
    candidates = []
    for p in Path(base_dir).glob("Meal Plan *.json"):
        m = _FILE_RE.match(p.name)
        if not m:
            continue
        file_date = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        if file_date <= today:
            candidates.append((file_date, p))
    if not candidates:
        return None
    return max(candidates, key=lambda x: x[0])[1]


def _qty_str(quantity_g: float, serving_size_g: float, unit_name: str | None) -> str:
    ratio = quantity_g / serving_size_g if serving_size_g else 1
    if unit_name:
        n = round(ratio, 1)
        n_str = str(int(n)) if n == int(n) else str(n)
        label = unit_name if n == 1 else unit_name + "s"
        return f"{n_str} {label}"
    return f"{round(quantity_g, 1)}g"


def _macros_from_ingredient(quantity_g: float, ing: dict) -> dict:
    serving_size_g = ing.get("serving_size_g") or ing.get("serving_size") or 1
    ratio = quantity_g / serving_size_g
    p = round(ratio * ing.get("protein_g", 0), 1)
    f = round(ratio * ing.get("fat_g", 0), 1)
    nc = round(ratio * max(ing.get("carbs_g", 0) - ing.get("fiber_g", 0), 0), 1)
    kcal = round(p * 4 + f * 9 + nc * 4)
    return {"kcal": str(kcal), "p": f"{p}g", "f": f"{f}g", "nc": f"{nc}g"}


def _ingredient_to_item(ing: dict) -> dict:
    quantity_g = ing["quantity_g"]
    serving_size_g = ing.get("serving_size_g") or ing.get("serving_size") or 1
    return {
        "food": ing["name"],
        "qty": _qty_str(quantity_g, serving_size_g, ing.get("unit_name")),
        **_macros_from_ingredient(quantity_g, ing),
    }


def _filler_to_item(entry: dict) -> dict:
    filler = entry["filler"]
    servings = entry["servings"]
    serving_size_g = filler.get("serving_size") or filler.get("serving_size_g") or 1
    quantity_g = servings * serving_size_g
    return {
        "food": filler["name"],
        "qty": _qty_str(quantity_g, serving_size_g, filler.get("unit_name")),
        **_macros_from_ingredient(quantity_g, filler),
    }


def sum_macros(items: list[dict]) -> dict:
    kcal = p = f = nc = 0.0
    for item in items:
        kcal += float(item.get("kcal", 0))
        p += float(str(item.get("p", "0")).rstrip("g"))
        f += float(str(item.get("f", "0")).rstrip("g"))
        nc += float(str(item.get("nc", "0")).rstrip("g"))
    return {"kcal": round(kcal), "p": round(p, 1), "f": round(f, 1), "nc": round(nc, 1)}


def parse_meal_plan(path: Path) -> dict:
    data = json.loads(path.read_text())
    result = {}
    for day in data["days"]:
        day_name = day["day_name"]
        meals = {}
        for meal_key, label in [("breakfast", "Breakfast"), ("lunch", "Lunch"), ("dinner", "Dinner")]:
            meal = day.get(meal_key)
            if not meal:
                continue
            items = [_ingredient_to_item(ing) for ing in meal.get("ingredients", [])]
            fillers = day.get(f"{meal_key}_fillers") or []
            items += [_filler_to_item(f) for f in fillers]
            if items:
                meals[label] = items
        result[day_name] = meals
    return result
