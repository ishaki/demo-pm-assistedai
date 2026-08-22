from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, List


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "AI-Assisted Preventive Maintenance POC"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database Configuration (MS SQL Server)
    DATABASE_URL: str = "mssql+pyodbc://sa:YourStrong!Passw0rd@mssql:1433/aiharvest_pm?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"

    # Schema management. When True, startup calls Base.metadata.create_all(),
    # which adds any missing tables. That is additive -- it never drops or
    # alters an existing table -- but it is still DDL issued against a live
    # database by whoever happens to restart the app.
    #
    # Set False to make the application completely read/write-data-only: it
    # issues no schema statements at all. Tables must then already exist, or be
    # created out of band with `python scripts/init_db.py`.
    #
    # deploy-app.sh sets this to False unless run with --with-db-init.
    DB_AUTO_CREATE_TABLES: bool = True

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

    # Demo reset -- the page at /demo-reset, reached from the sidebar copyright.
    #
    # The endpoint behind it DELETES every machine, work order, AI decision,
    # maintenance record and workflow log, then reseeds. Three gates, all in
    # routers/admin.py:
    #   DEMO_RESET_ENABLED=False  -> 403, the endpoint is inert
    #   DEMO_RESET_TOKEN empty    -> 503, rather than silently open
    #   wrong or missing token    -> 401
    #
    # Set the token to something only the person running the demo knows. There
    # is no other authentication anywhere in this application, so this one
    # value is all that stands between a public URL and an empty database.
    DEMO_RESET_ENABLED: bool = True
    DEMO_RESET_TOKEN: Optional[str] = ""

    # Defaults the reset page prefills. DEMO_ADMIN_EMAIL receives the work order
    # approval notice, DEMO_SUPPLIER_EMAIL the supplier notification; a reset
    # writes them to every seeded machine's admin_email / supplier_email.
    DEMO_ADMIN_EMAIL: str = "ishak.ahmad@innoark.com"
    DEMO_SUPPLIER_EMAIL: str = "natalia4nib@gmail.com"

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
