from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os

class Settings(BaseSettings):
    APP_NAME: str = "ZamID Connect API"
    APP_ENV: str = "development"
    APP_PORT: int = 8000
    APP_DEBUG: bool = True
    SECRET_KEY: str

    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # JWT
    JWT_ACCESS_SECRET: str
    JWT_REFRESH_SECRET: str
    JWT_ACCESS_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    # QR Signing (v2 JWT — one-time tokens)
    # Use a strong random secret: python -c "import secrets; print(secrets.token_hex(32))"
    QR_SIGNING_SECRET: str = "zamid_qr_secret_CHANGE_ME"
    QR_TOKEN_EXPIRE_SECONDS: int = 60        # Time window for QR token validity

    # Redis (for production token blacklist — replaces in-memory set in qr_service.py)
    # Leave empty to use in-memory blacklist (fine for single-instance deployments)
    REDIS_URL: str = ""

    # CORS
    ALLOWED_ORIGINS: str = "*"

    @property
    def origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    # Rate Limiting
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_VERIFY: str = "30/minute"
    RATE_LIMIT_USSD: str = "200/minute"
    RATE_LIMIT_GLOBAL: str = "100/minute"

    # Account Lockout
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 30

    # Africa's Talking
    AT_USERNAME: str = "sandbox"  # change to "zamid" in production
    AT_API_KEY: str = "your_key"
    AT_USSD_CODE: str = "*384*98008#"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
