from datetime import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    trmnl_webhook_url: str
    breakfast_time: str = "07:00"
    lunch_time: str = "12:00"
    dinner_time: str = "18:00"
    timezone: str = "America/Indiana/Indianapolis"
    meal_plan_dir: str = "/mealplans"

    @model_validator(mode="after")
    def validate_fields(self) -> "Settings":
        self._parse_time(self.breakfast_time)
        self._parse_time(self.lunch_time)
        self._parse_time(self.dinner_time)
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError:
            raise ValueError(f"Unknown timezone: {self.timezone!r}")
        return self

    @staticmethod
    def _parse_time(s: str) -> time:
        h, m = s.split(":")
        return time(int(h), int(m))

    @property
    def breakfast(self) -> time:
        return self._parse_time(self.breakfast_time)

    @property
    def lunch(self) -> time:
        return self._parse_time(self.lunch_time)

    @property
    def dinner(self) -> time:
        return self._parse_time(self.dinner_time)

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


settings = Settings()
