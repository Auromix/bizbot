"""全局配置管理

所有用户可配置项均通过 .env 文件设置，运行时自动加载到此处。
默认使用 MiniMax 作为 LLM 提供商。

使用方式：
    1. 运行 python scripts/setup_env.py 生成 .env 文件
    2. 或手动创建 .env 文件（参考 .env.example）
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置 - 所有字段均可通过 .env 或环境变量覆盖"""

    # ========== MiniMax LLM 配置（默认） ==========
    minimax_api_key: str = ""
    minimax_model: str = "MiniMax-M2.5"
    minimax_base_url: str = "https://api.minimaxi.com/anthropic"

    # ========== 数据库 ==========
    database_url: str = "sqlite:///data/store.db"

    # ========== Web 平台配置 ==========
    web_host: str = "0.0.0.0"
    web_port: int = 8080
    web_username: str = "admin"
    web_password: str = "admin123"
    web_secret_key: str = "change-me-to-a-random-secret-key"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# 全局配置实例
settings = Settings()
