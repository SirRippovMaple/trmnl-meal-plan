import re
from datetime import date
from pathlib import Path

_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_MEAL_NAMES = {"Breakfast", "Lunch", "Dinner", "Snacks"}
_STOP_SECTIONS = {"Weekly Summary", "Shopping List"}
_FILE_DATE_RE = re.compile(r"meal-plan-(\d{4}-\d{2}-\d{2})\.md$")
_PANTRY_TAG_RE = re.compile(r"\s*\*\([^)]*\)\*")
_COOKING_RE = re.compile(r"\s*—\s*.+$")


def find_current_file(meal_plan_dir: str, today: date) -> Path | None:
    candidates: list[tuple[date, Path]] = []
    for p in Path(meal_plan_dir).glob("meal-plan-*.md"):
        m = _FILE_DATE_RE.match(p.name)
        if m:
            file_date = date.fromisoformat(m.group(1))
            if file_date <= today:
                candidates.append((file_date, p))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def _extract_day(heading: str) -> str | None:
    first_word = heading.split()[0] if heading.strip() else ""
    if first_word in _DAY_NAMES and "Batch Prep" not in heading:
        return first_word
    return None


def _clean_food(raw: str) -> str:
    name = _PANTRY_TAG_RE.sub("", raw)
    name = _COOKING_RE.sub("", name)
    return name.strip()


def _parse_num(s: str) -> float:
    cleaned = re.sub(r"[~,g✓\s]", "", s)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def parse_meal_plan(path: Path) -> dict[str, dict[str, list[dict]]]:
    """
    Returns {day_name: {meal_type: [{"food", "qty", "kcal", "p", "f", "nc"}]}}
    """
    result: dict[str, dict[str, list[dict]]] = {}
    current_day: str | None = None
    in_table = False
    current_meal: str | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if line.startswith("## "):
            heading = line[3:].strip()

            if any(heading.startswith(s) for s in _STOP_SECTIONS):
                break

            day = _extract_day(heading)
            current_day = day
            in_table = False
            current_meal = None
            if day and day not in result:
                result[day] = {m: [] for m in _MEAL_NAMES}
            continue

        if current_day is None:
            continue

        # Table header detection
        if line.startswith("| Meal |"):
            in_table = True
            continue

        # Separator row
        if line.startswith("|---") or line.startswith("| ---"):
            continue

        if not in_table:
            continue

        if not line.startswith("|"):
            in_table = False
            continue

        cells = [c.strip() for c in line.split("|")]
        # Expect at least 8 cells: ['', meal, food, qty, kcal, p, f, nc, '']
        if len(cells) < 8:
            continue

        meal_cell = cells[1]
        food_cell = cells[2]

        # Skip TOTAL row
        if "TOTAL" in meal_cell or "**TOTAL**" in meal_cell:
            continue

        # Update current meal when cell is non-empty
        if meal_cell:
            normalized = meal_cell.title()
            if normalized in _MEAL_NAMES:
                current_meal = normalized

        if current_meal is None:
            continue

        food = _clean_food(food_cell)
        if not food:
            continue

        result[current_day][current_meal].append(
            {
                "food": food,
                "qty": cells[3],
                "kcal": cells[4],
                "p": cells[5],
                "f": cells[6],
                "nc": cells[7] if len(cells) > 7 else "0",
            }
        )

    return result


def sum_macros(items: list[dict]) -> dict:
    return {
        "kcal": round(sum(_parse_num(i["kcal"]) for i in items)),
        "p": round(sum(_parse_num(i["p"]) for i in items)),
        "f": round(sum(_parse_num(i["f"]) for i in items)),
        "nc": round(sum(_parse_num(i["nc"]) for i in items), 1),
    }
