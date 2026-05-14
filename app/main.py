import logging
from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

from .config import settings
from .publisher import publish
from .renderer import render_png
from .resolver import infer_meal_type, resolve

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone=settings.timezone)


def _scheduled_publish(meal_type: str) -> None:
    try:
        publish(meal_type, settings)
    except Exception as exc:
        logger.error("Scheduled publish failed for %s: %s", meal_type, exc)


def _add_jobs() -> None:
    for meal_type, t in [
        ("Breakfast", settings.breakfast),
        ("Lunch", settings.lunch),
        ("Dinner", settings.dinner),
    ]:
        scheduler.add_job(
            _scheduled_publish,
            CronTrigger(hour=t.hour, minute=t.minute, timezone=settings.timezone),
            args=[meal_type],
            id=meal_type.lower(),
            replace_existing=True,
        )
        logger.info("Scheduled %s at %02d:%02d %s", meal_type, t.hour, t.minute, settings.timezone)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _add_jobs()
    scheduler.start()
    try:
        publish(None, settings)
    except Exception as exc:
        logger.warning("Startup publish failed (non-fatal): %s", exc)
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="TRMNL Meal Plan Publisher", lifespan=lifespan)


@app.get("/health")
def health():
    now = datetime.now(tz=settings.tz)
    jobs = {j.id: str(j.next_run_time) for j in scheduler.get_jobs()}
    return {
        "status": "ok",
        "current_time": now.strftime("%H:%M"),
        "current_meal": infer_meal_type(now, settings),
        "next_runs": jobs,
    }


@app.get("/display", response_class=Response)
def display(
    meal_type: str = Query(default="auto", description="auto, breakfast, lunch, or dinner")
):
    normalized = meal_type.strip().lower()
    type_map = {"breakfast": "Breakfast", "lunch": "Lunch", "dinner": "Dinner", "auto": None}
    if normalized not in type_map:
        raise HTTPException(status_code=400, detail=f"Invalid meal_type {meal_type!r}")
    data = resolve(type_map[normalized], settings)
    return Response(content=render_png(data), media_type="image/png")


@app.post("/publish")
def manual_publish(
    meal_type: str = Query(default="auto", description="auto, breakfast, lunch, or dinner")
):
    normalized = meal_type.strip().lower()
    type_map = {"breakfast": "Breakfast", "lunch": "Lunch", "dinner": "Dinner", "auto": None}
    if normalized not in type_map:
        raise HTTPException(status_code=400, detail=f"Invalid meal_type {meal_type!r}")
    try:
        data = publish(type_map[normalized], settings)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"published": data["meal_type"], "day": data["day"]}
