# -*- coding: utf-8 -*-
"""全局配置（生产版）

环境变量读取策略：
1. Railway: 通过 Dashboard 设置
2. Neon: 提供 DATABASE_URL
3. Vercel: 通过 Environment Variables 设置
4. Local: 通过 .env 文件
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """应用配置"""

    # === DeepSeek API ===
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

    # === Database ===
    # Railway: 使用 Neon PostgreSQL
    # Local:    sqlite:///./app.db
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./app.db",
    )

    # === CORS ===
    # 生产环境: https://your-app.vercel.app
    # 多个域名用逗号分隔
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:4173",
    ).split(",")

    # === File Upload ===
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", str(50 * 1024 * 1024)))

    # === Security ===
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15

    # === Logging ===
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")


settings = Settings()
