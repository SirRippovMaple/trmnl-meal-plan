from datetime import datetime

from .config import Settings
from .json_meal_parser import find_current_file, parse_meal_plan, sum_macros


def infer_meal_type(now: datetime, s: Settings) -> str:
    t = now.time()
    if t >= s.dinner:
        return "Dinner"
    if t >= s.lunch:
        return "Lunch"
    if t >= s.breakfast:
        return "Breakfast"
    return "Dinner"  # before breakfast — show last meal


def resolve(meal_type: str | None, settings: Settings) -> dict:
    """
    Returns {
        "meal_type": str,
        "day": str,
        "week_date": str,
        "items": [{"food", "qty", "kcal", "p", "f", "nc"}],
        "macros": {"kcal", "p", "f", "nc"},
        "error": str | None,
    }
    """
    now = datetime.now(tz=settings.tz)
    resolved_type = meal_type or infer_meal_type(now, settings)
    day_name = now.strftime("%A")

    meal_file = find_current_file(settings.meal_plan_dir, now.date())
    if meal_file is None:
        return _error(resolved_type, day_name, now, "No meal plan file found for this week.")

    try:
        week_dt = datetime.strptime(meal_file.stem.replace("Meal Plan ", ""), "%Y-%m-%d")
        week_label = week_dt.strftime("%B %-d, %Y")
    except ValueError:
        week_label = meal_file.stem

    plan = parse_meal_plan(meal_file)

    if day_name not in plan:
        return _error(resolved_type, day_name, week_label, f"No entry for {day_name} in this week's plan.")

    items = plan[day_name].get(resolved_type, [])
    if not items:
        return _error(resolved_type, day_name, week_label, f"No {resolved_type.lower()} planned for {day_name}.")

    return {
        "meal_type": resolved_type,
        "day": day_name,
        "week_date": week_label,
        "items": items,
        "macros": sum_macros(items),
        "error": None,
    }


def _error(meal_type: str, day: str, week_date: str, message: str) -> dict:
    return {
        "meal_type": meal_type,
        "day": day,
        "week_date": week_date,
        "items": [],
        "macros": {},
        "error": message,
    }
