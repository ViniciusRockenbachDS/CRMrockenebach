"""Configurações centrais da aplicação, carregadas de variáveis de ambiente / .env."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url

_INSECURE_DEFAULT_SECRET = "troque-esta-chave-em-producao-use-pelo-menos-32-caracteres"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Aplicação ---------------------------------------------------------
    APP_NAME: str = "CRM API"
    APP_ENV: Literal["development", "staging", "production", "test"] = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    TIMEZONE: str = "America/Sao_Paulo"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "http://localhost:5173"

    # --- Banco ------------------------------------------------------------------
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "crm"
    POSTGRES_PASSWORD: SecretStr = SecretStr("crm_dev_password")
    POSTGRES_DB: str = "crm"
    DATABASE_URL: str | None = None
    TEST_DATABASE_URL: str | None = None

    DB_ECHO: bool = False
    DB_POOL_SIZE: int = Field(default=10, ge=1)
    DB_MAX_OVERFLOW: int = Field(default=20, ge=0)

    # --- JWT --------------------------------------------------------------------
    JWT_SECRET_KEY: SecretStr = SecretStr(_INSECURE_DEFAULT_SECRET)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=1)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1)

    FIRST_ADMIN_NAME: str = "Administrador"
    FIRST_ADMIN_EMAIL: str = "admin@crm.local"
    FIRST_ADMIN_PASSWORD: SecretStr = SecretStr("Admin@12345")

    # --- Paginação ---------------------------------------------------------------
    PAGINATION_DEFAULT_LIMIT: int = Field(default=20, ge=1)
    PAGINATION_MAX_LIMIT: int = Field(default=100, ge=1)

    # --- IA ---------------------------------------------------------------------
    AI_ENABLED: bool = True
    AI_PROVIDER: Literal["stub", "openai", "anthropic"] = "stub"
    AI_MODEL: str = ""
    AI_API_KEY: SecretStr | None = None
    AI_TIMEOUT_SECONDS: int = Field(default=30, ge=1)
    AI_CACHE_TTL_HOURS: int = Field(default=24, ge=0)

    # ---------------------------------------------------------------------------
    @model_validator(mode="after")
    def _validate_security(self) -> "Settings":
        if self.APP_ENV == "production":
            secret = self.JWT_SECRET_KEY.get_secret_value()
            if secret == _INSECURE_DEFAULT_SECRET or len(secret) < 32:
                raise ValueError(
                    "JWT_SECRET_KEY precisa ser definida com pelo menos 32 caracteres em produção."
                )
            if self.DEBUG:
                raise ValueError("DEBUG não pode ficar ativo em produção.")
        if self.AI_PROVIDER != "stub" and self.AI_ENABLED:
            if not self.AI_API_KEY:
                raise ValueError(f"AI_API_KEY é obrigatória quando AI_PROVIDER={self.AI_PROVIDER}.")
            if not self.AI_MODEL:
                raise ValueError(f"AI_MODEL é obrigatório quando AI_PROVIDER={self.AI_PROVIDER}.")
        return self

    @property
    def database_url(self) -> URL:
        """URL assíncrona (asyncpg). URL.create escapa caracteres especiais da senha."""
        if self.DATABASE_URL:
            return make_url(self.DATABASE_URL)
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD.get_secret_value(),
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
