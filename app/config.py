from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # Supabase (Pydantic mapeará AUTOMÁTICAMENTE SUPABASE_URL a supabase_url)
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_jwt_secret: str

    # App
    app_env: str = "development"
    app_version: str = "1.0.0"

    # CORS - Asegúrate de que en el .env diga ALLOWED_ORIGINS
    allowed_origins: str = "http://localhost:3000,http://localhost:9002"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    # Configuración para Pydantic V2 (la que tienes instalada)
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore" # Esto evita errores si tienes más variables en el .env
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()