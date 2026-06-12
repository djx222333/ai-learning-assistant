# -*- coding: utf-8 -*-
"""閸忋劌鐪柊宥囩枂閿涘牏鏁撴禍褏澧楅敍?
閻滎垰顣ㄩ崣姗€鍣虹拠璇插絿缁涙牜鏆愰敍?1. Railway: 闁俺绻?Dashboard 鐠佸墽鐤?2. Neon: 閹绘劒绶?DATABASE_URL
3. Vercel: 闁俺绻?Environment Variables 鐠佸墽鐤?4. Local: 闁俺绻?.env 閺傚洣娆?"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """鎼存梻鏁ら柊宥囩枂"""

    # === DeepSeek API ===
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

    # === Database ===
    # Railway: 娴ｈ法鏁?Neon PostgreSQL
    # Local:    sqlite:///./app.db
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./app.db",
    )

    # === CORS ===
    # 閻㈢喍楠囬悳顖氼暔: https://your-app.vercel.app
    # 婢舵矮閲滈崺鐔锋倳閻劑鈧褰块崚鍡涙
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:4173",
    ).split(",")

    # === File Upload ===
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", str(50 * 1024 * 1024)))

    # === Security ===
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15

    # === Logging ===
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")




# ============================================================
# 环境变量诊断（不改变业务逻辑，仅用于 /env-check 和日志）
# ============================================================

POSTGRES_ENV_VARS = [
    "DATABASE_URL",
    "POSTGRES_URL",
    "POSTGRESQL_URL",
    "PGHOST",
    "PGPORT",
    "PGDATABASE",
    "PGUSER",
    "PGPASSWORD",
    "NEON_DATABASE_URL",
    "RAILWAY_DATABASE_URL",
]


def check_env_vars() -> list[dict]:
    """检查所有可能的 PostgreSQL 环境变量
    
    返回每个变量的存在状态和值（已脱敏）
    """
    results = []
    for name in POSTGRES_ENV_VARS:
        value = os.environ.get(name, "")
        exists = bool(value and value.strip())
        safe_value = ""
        if exists:
            if "://" in value and "@" in value:
                # URL 类型: 隐藏密码
                try:
                    parts = value.split("@")
                    creds = parts[0].rsplit(":", 1)
                    if len(creds) == 2:
                        safe_value = creds[0] + ":***@" + parts[1]
                    else:
                        safe_value = value[:40] + "..."
                except Exception:
                    safe_value = value[:40] + "..."
            elif "://" in value:
                safe_value = value[:40] + "..."
            else:
                # 普通值: 只显示前几个字符
                safe_value = value[:20] + "..." if len(value) > 20 else value
        results.append({
            "name": name,
            "exists": exists,
            "value_masked": safe_value,
        })
    return results


def get_database_url_from_any_env() -> str | None:
    """尝试从多个环境变量名获取 DATABASE_URL
    
    Railway 可能使用不同变量名注入 PostgreSQL 连接信息。
    优先级: DATABASE_URL > POSTGRES_URL > POSTGRESQL_URL > PGHOST 组合
    """
    # 优先级 1: 标准 DATABASE_URL
    url = os.environ.get("DATABASE_URL", "").strip()
    if url and url.startswith("postgres"):
        return url

    # 优先级 2: POSTGRES_URL
    url = os.environ.get("POSTGRES_URL", "").strip()
    if url and url.startswith("postgres"):
        return url

    # 优先级 3: POSTGRESQL_URL
    url = os.environ.get("POSTGRESQL_URL", "").strip()
    if url and url.startswith("postgres"):
        return url

    # 优先级 4: 从 PGHOST + PGPORT 组合
    host = os.environ.get("PGHOST", "").strip()
    port = os.environ.get("PGPORT", "5432").strip()
    db = os.environ.get("PGDATABASE", "").strip()
    user = os.environ.get("PGUSER", "").strip()
    password = os.environ.get("PGPASSWORD", "").strip()
    if host and user:
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"

    return None

settings = Settings()




