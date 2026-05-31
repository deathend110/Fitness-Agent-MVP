from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 配置文件固定放在 backend 目录中，确保本地 Python 服务与前端工作区解耦。
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 数据目录默认跟随后端工作目录，不额外写入系统盘的公共位置。
    data_dir: str = "./data"
    database_url: str = "sqlite+aiosqlite:///./data/repmind.db"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # DeepSeek 密钥只允许保存在后端 .env 中，前端 bundle 永不直接读取。
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    default_model: str = "deepseek-chat"


@lru_cache
def get_settings() -> Settings:
    # 缓存配置对象，避免应用启动后重复读取环境变量。
    settings = Settings()
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    return settings
