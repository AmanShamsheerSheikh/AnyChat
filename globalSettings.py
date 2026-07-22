from typing import Tuple, Type
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, YamlConfigSettingsSource
from pathlib import Path

BASE_DIR = Path(__file__).parent
class LLMSettings(BaseSettings):
    model_name: str
    temperature: float
    max_tokens: int
    gpu_memory_utilization: float
    model_config = SettingsConfigDict(yaml_file=BASE_DIR/"model.yaml", env_file_encoding="utf-8")
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        **kwargs
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (YamlConfigSettingsSource(settings_cls),)

class PGSettings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    PGBOUNCER_PORT: int
    PGBOUNCER_POOL_MODE: str
    PGBOUNCER_MAX_CLIENT_CONN: int
    PGBOUNCER_DEFAULT_POOL_SIZE: int
    PGBOUNCER_MAX_CONNECTIONS: int
    PGBOUNCER_MIN_CONNECTIONS: int
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

class ApiSettings(BaseSettings):
    hf_token: str
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

class RedisSettings(BaseSettings):
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_PASSWORD: str | None
    REDIS_DECODE_RESPONSES: bool
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")