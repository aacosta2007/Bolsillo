from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore", case_sensitive=False)

    database_url: str = "mysql+asyncmy://bolsillo:bolsillo@localhost:3306/bolsillo?charset=utf8mb4"
    # Obligatorio: sin valor por defecto para no arrancar nunca con un secreto conocido
    jwt_secret: str = Field(min_length=32)
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    cookie_secure: bool = True
    default_timezone: str = "America/Bogota"
    default_currency: str = "COP"
    initial_user_email: str = ""
    initial_user_password: str = ""
    # Lista separada por comas; vacío = sin CORS (producción, mismo origen)
    cors_origins: str = ""
    login_max_failures: int = 5
    login_window_seconds: int = 300
    # Web Push (VAPID). Opcionales: sin claves solo se usa la bandeja. Ver `python -m app.cli gen-vapid`.
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = ""  # mailto:... (si falta se usa uno por defecto)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
