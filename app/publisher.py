import logging

import httpx

from .config import Settings
from .renderer import render_png
from .resolver import resolve

logger = logging.getLogger(__name__)


def publish(meal_type: str | None, settings: Settings) -> dict:
    data = resolve(meal_type, settings)
    png = render_png(data)

    resp = httpx.post(
        settings.trmnl_webhook_url,
        content=png,
        headers={"Content-Type": "image/png"},
        timeout=15,
    )
    resp.raise_for_status()
    logger.info(
        "Published %s for %s → HTTP %s (%d bytes)",
        data["meal_type"], data["day"], resp.status_code, len(png),
    )
    return data
