from pydantic_settings import BaseSettings
from pydantic import Field
from pydantic import ConfigDict


class Settings(BaseSettings):

    model_config = ConfigDict(
        env_file=".env",
        extra="ignore"
    )

    # API Keys
    sarvam_api_key: str = Field(..., alias="SARVAM_API_KEY")
    groq_api_key: str = Field(..., alias="GROQ_API_KEY")

    # LLM
    llm_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.4
    llm_top_p: float = 0.9
    llm_max_tokens: int = 512

    # TTS
    tts_model: str = "bulbul:v3-beta"
    tts_voice: str = "shubh"
    tts_pace: float = 0.95
    tts_temperature: float = 0.6

    # Inactivity
    max_reminders: int = 3
    reminder_interval: int = 15


settings = Settings()