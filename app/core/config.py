import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    DATABASE_URL: str | None = None
    GEMINI_API_KEY: str | None = None
    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    TWILIO_WHATSAPP_NUMBER: str | None = None
    REDIS_URL: str | None = None
    NEWS_API_KEY: str | None = None
    GOOGLE_MAPS_API_KEY: str | None = None
    class Config:
        case_sensitive = True

settings = Settings()