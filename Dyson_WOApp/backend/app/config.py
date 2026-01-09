from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, List


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "AI-Assisted Preventive Maintenance POC"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database Configuration (MS SQL Server)
    DATABASE_URL: str = "mssql+pyodbc://sa:YourStrong!Passw0rd@mssql:1433/dyson_pm?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"

    # LLM Configuration
    LLM_PROVIDER: str = "openai"  # Options: openai, claude, gemini
    OPENAI_API_KEY: Optional[str] = ""
    ANTHROPIC_API_KEY: Optional[str] = ""
    GOOGLE_API_KEY: Optional[str] = ""
    LLM_MODEL: Optional[str] = None  # Provider-specific model (auto-selected if not set)

    # AI Decision Threshold
    CONFIDENCE_THRESHOLD: float = 0.7

    # SMTP Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = ""
    SMTP_PASSWORD: Optional[str] = ""
    SMTP_FROM_EMAIL: Optional[str] = ""
    SMTP_USE_TLS: bool = True

    # PM Detection Window
    PM_DUE_DAYS: int = 30

    # CORS Configuration (comma-separated string in .env, e.g., "http://localhost:3000,http://frontend:3000")
    CORS_ORIGINS: str = "http://localhost:3000,http://frontend:3000"

    # API Configuration
    API_V1_PREFIX: str = "/api/v1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def get_cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into a list"""
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        return self.CORS_ORIGINS


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Using lru_cache to avoid reading .env file multiple times.
    """
    return Settings()
