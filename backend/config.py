import os
from collections.abc import MutableMapping
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent
PROXY_ENV_FIELD_MAP = {
    "http_proxy": "HTTP_PROXY",
    "https_proxy": "HTTPS_PROXY",
    "all_proxy": "ALL_PROXY",
    "no_proxy": "NO_PROXY",
}


def resolve_backend_relative_path(raw_path: str) -> str:
    """把后端配置里的相对路径统一锚定到 backend 目录，避免启动目录不同导致路径漂移。"""

    if not raw_path:
        return raw_path
    path = Path(raw_path)
    if path.is_absolute():
        return raw_path
    return str((BACKEND_DIR / path).resolve())


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
    uploads_dir: str = "./data/uploads"
    model_provider_config_path: str = "./config/model_providers.json"
    database_url: str = "sqlite+aiosqlite:///./data/repmind.db"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    max_upload_mb: int = 15
    allowed_upload_extensions: list[str] = Field(
        default_factory=lambda: [
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".xlsx",
            ".xlsm",
            ".docx",
            ".md",
            ".txt",
        ]
    )

    # DeepSeek 密钥只允许保存在后端 .env 中，前端 bundle 永不直接读取。
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    default_model: str = "deepseek-v4-flash"
    model_allowlist: list[str] = Field(
        default_factory=lambda: ["deepseek-v4-flash", "deepseek-v4-pro"]
    )
    default_thinking_enabled: bool = False
    default_thinking_budget: str = "auto"
    deepseek_timeout_seconds: float = 30.0
    # Gemini 等海外模型在部分网络环境下必须经过代理，这里显式接入 backend/.env，
    # 避免只在启动终端里临时设置代理时，后端重启或换启动方式后又悄悄失效。
    http_proxy: str = ""
    https_proxy: str = ""
    all_proxy: str = ""
    no_proxy: str = ""

    @model_validator(mode="after")
    def normalize_local_paths(self) -> "Settings":
        data_path = Path(self.data_dir)
        if not data_path.is_absolute():
            self.data_dir = str((BACKEND_DIR / data_path).resolve())
        uploads_path = Path(self.uploads_dir)
        if not uploads_path.is_absolute():
            self.uploads_dir = str((BACKEND_DIR / uploads_path).resolve())
        self.model_provider_config_path = resolve_backend_relative_path(self.model_provider_config_path)
        self.database_url = resolve_sqlite_url(self.database_url)
        return self


def apply_runtime_proxy_environment(
    settings: Settings,
    env: MutableMapping[str, str] | None = None,
) -> dict[str, str]:
    """把 settings 中声明的代理同步回进程环境，确保 httpx 等库能稳定读取。"""

    target_env = env if env is not None else os.environ
    applied: dict[str, str] = {}
    for field_name, env_name in PROXY_ENV_FIELD_MAP.items():
        raw_value = getattr(settings, field_name, "")
        proxy_value = str(raw_value or "").strip()
        if not proxy_value:
            continue
        target_env[env_name] = proxy_value
        target_env[env_name.lower()] = proxy_value
        applied[env_name] = proxy_value
    return applied


@lru_cache
def get_settings() -> Settings:
    # 缓存配置对象，避免应用启动后重复读取环境变量。
    settings = Settings()
    apply_runtime_proxy_environment(settings)
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.uploads_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.model_provider_config_path).parent.mkdir(parents=True, exist_ok=True)
    return settings
