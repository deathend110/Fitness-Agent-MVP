import uvicorn

from backend.config import get_settings


def main() -> None:
    settings = get_settings()

    # 开发环境统一从 backend/.env 读取主机和端口，避免 package.json 与配置层重复维护。
    uvicorn.run(
        "backend.main:app",
        reload=True,
        host=settings.backend_host,
        port=settings.backend_port,
    )


if __name__ == "__main__":
    main()
