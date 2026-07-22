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

class ApiSettings(BaseSettings):
    hf_token: str
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

api_settings = ApiSettings()
llm_settings = LLMSettings()