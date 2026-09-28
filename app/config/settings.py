from functools import lru_cache
import http

from pydantic_settings import BaseSettings, SettingsConfigDict # type: ignore


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables
    and the .env file.
    """

    # ---------------------------------------------------------
    # Application
    # ---------------------------------------------------------

    app_name: str = "Hospital Operations Intelligence System"
    app_env: str = "development"
    debug: bool = True

    # ---------------------------------------------------------
    # MySQL Database
    # ---------------------------------------------------------

    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "hospital_ai"
    db_user: str = "root"
    db_password: str = ""

    # ---------------------------------------------------------
    # LLM
    # ---------------------------------------------------------

    llm_provider: str = "openai"
    llm_model: str = ""
    openai_api_key: str = ""
    
    # ---------------------------------------------------------
    # Notification Service
    # ---------------------------------------------------------
    N8N_WEBHOOK_URL: str
    N8N_WEBHOOK_TIMEOUT: int = 10

    # ---------------------------------------------------------
    # API
    # ---------------------------------------------------------

    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # ---------------------------------------------------------
    # Pydantic Settings Configuration
    # ---------------------------------------------------------

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached Settings object.

    The configuration is loaded once and reused
    throughout the application.
    """

    return Settings()