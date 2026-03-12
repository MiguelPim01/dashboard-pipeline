from functools import lru_cache
from dotenv import load_dotenv
import os

from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    THEMES_ARRAY: str = os.getenv("THEMES_ARRAY", "")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
