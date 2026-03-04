from pydantic_settings import BaseSettings
from pydantic import Field
from pydantic import ConfigDict
from typing import List


class Settings(BaseSettings):

    model_config = ConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=True
    )

    # =====================================================
    # 🔑 API KEYS
    # =====================================================
    sarvam_api_key: str = Field(..., alias="SARVAM_API_KEY")
    groq_api_key: str = Field(..., alias="GROQ_API_KEY")

    # =====================================================
    # 🗄 DATABASE
    # =====================================================
    database_url: str = Field(..., alias="DATABASE_URL")

    # =====================================================
    # 👤 ADMIN SEEDER
    # =====================================================
    admin_email: str = Field(..., alias="ADMIN_EMAIL")
    admin_password: str = Field(..., alias="ADMIN_PASSWORD")
    full_name: str = Field(..., alias="ADMIN_FULLNAME")
    

    # =====================================================
    # 🤖 LLM CONFIG
    # =====================================================
    llm_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.4
    llm_top_p: float = 0.9
    llm_max_tokens: int = 512

    # =====================================================
    # 🔊 TTS CONFIG
    # =====================================================
    tts_model: str = "bulbul:v3-beta"
    tts_voice: str = "shubh"
    tts_pace: float = 0.95
    tts_temperature: float = 0.6

    # =====================================================
    # ⏳ INACTIVITY SETTINGS
    # =====================================================
    max_reminders: int = 3
    reminder_interval: int = 15

    # =====================================================
    # 🔐 SECURITY SETTINGS
    # =====================================================
    SECRET_KEY: str = Field(..., alias="SECRET_KEY")
    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        15,
        alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        7,
        alias="REFRESH_TOKEN_EXPIRE_DAYS"
    )

    # Allowed CORS origins (Production Safe)
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000"],
        alias="ALLOWED_ORIGINS"
    )

    # Rate limiting
    LOGIN_RATE_LIMIT: str = Field(
        "5/minute",
        alias="LOGIN_RATE_LIMIT"
    )

    # Account lock settings
    MAX_LOGIN_ATTEMPTS: int = Field(
        5,
        alias="MAX_LOGIN_ATTEMPTS"
    )

    ACCOUNT_LOCK_MINUTES: int = Field(
        15,
        alias="ACCOUNT_LOCK_MINUTES"
    )

    # Environment
    ENVIRONMENT: str = Field(
        "development",
        alias="ENVIRONMENT"
    )


settings = Settings()