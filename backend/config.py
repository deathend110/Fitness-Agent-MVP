from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent


def resolve_sqlite_url(database_url: str) -> str:
    sqlite_prefix = "sqlite+aiosqlite:///"
    if database_url == "sqlite+aiosqlite:///:memory:" or not database_url.startswith(sqlite_prefix):
        return database_url

    raw_path = database_url.removeprefix(sqlite_prefix)
    path = Path(raw_path)
    if path.is_absolute():
        return database_url

    # 本地 SQLite 相对路径统一以 backend/ 为基准，避免从仓库根目录启动时误写到 ./data。
    resolved_path = (BACKEND_DIR / path).resolve()
    return f"{sqlite_prefix}{resolved_path.as_posix()}"


class Settings(BaseSettings):
    # 配置文件固定放在 backend 目录中，确保本地 Python 服务与前端工作区解耦。
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
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
    default_model: str = "deepseek-v4-flash"
    deepseek_timeout_seconds: float = 30.0

    @model_validator(mode="after")
    def normalize_local_paths(self) -> "Settings":
        data_path = Path(self.data_dir)
        if not data_path.is_absolute():
            self.data_dir = str((BACKEND_DIR / data_path).resolve())
        self.database_url = resolve_sqlite_url(self.database_url)
        return self


@lru_cache
def get_settings() -> Settings:
    # 缓存配置对象，避免应用启动后重复读取环境变量。
    settings = Settings()
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    return settings
