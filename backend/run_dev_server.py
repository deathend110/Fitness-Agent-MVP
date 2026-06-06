import uvicorn
import os

from backend.config import get_settings


def main() -> None:
    settings = get_settings()
    reload_enabled = os.environ.get("REPMIND_BACKEND_RELOAD", "1").strip().lower() not in {
        "0",
        "false",
        "no",
    }

    # 开发环境统一从 backend/.env 读取主机和端口，避免 package.json 与配置层重复维护。
    uvicorn.run(
        "backend.main:app",
        reload=reload_enabled,
        host=settings.backend_host,
        port=settings.backend_port,
    )


if __name__ == "__main__":
    main()
