# -*- coding: utf-8 -*-
"""认证服务：密码哈希 + JWT 令牌管理

职责链：
  register()
    ├── hash_password(password) → bcrypt hashed
    ├── INSERT users 表
    └── return User

  login()
    ├── SELECT user by username
    ├── verify_password(plain, hashed)
    ├── create_access_token({sub: user_id})
    └── return {access_token, user}

  get_current_user()
    ├── decode token from Authorization header
    ├── SELECT user by id
    └── return User ORM obj (or 401)

设计原则：
1. 密码只存 bcrypt hash，永不存明文
2. JWT payload 只存 user_id（sub），不存敏感信息
3. Token 过期由客户端重新登录（当前不做 refresh token）
4. 所有依赖注入通过 FastAPI Depends 链式调用
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.models import User

# ---- BCrypt 密码上下文 ----
# schemes=["bcrypt"] 指定使用 bcrypt 算法
# deprecated="auto" 自动处理过时算法升级
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---- OAuth2 密码 Bearer 模式 ----
# tokenUrl="/api/v1/auth/login" 用于 Swagger UI "Authorize" 按钮
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ============================================================
# 密码处理
# ============================================================

def hash_password(password: str) -> str:
    """使用 bcrypt 对密码进行哈希

    bcrypt 特点：
    - 自动加盐（salt）
    - 可配置计算成本（cost factor）
    - 相同密码每次哈希结果不同

    Args:
        password: 明文密码

    Returns:
        bcrypt 哈希字符串（如 $2b$12$...）
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与 bcrypt 哈希是否匹配

    使用 passlib 自动处理：
    - 从 hash 中提取 salt
    - 对明文执行相同哈希
    - 比较结果

    Args:
        plain_password: 用户输入的明文密码
        hashed_password: 数据库中存储的 bcrypt 哈希

    Returns:
        True 匹配 / False 不匹配
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================
# JWT 令牌管理
# ============================================================

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """创建 JWT Access Token

    JWT 结构：
    Header:  { "alg": "HS256", "typ": "JWT" }
    Payload: { "sub": user_id, "exp": timestamp, ... }
    Signature: HMAC-SHA256(base64(header) + "." + base64(payload), secret)

    Args:
        data: 要编码到 token 中的数据（必须包含 "sub" 字段）
        expires_delta: 过期时间（可选，默认使用 settings 配置）

    Returns:
        JWT 字符串（如 eyJhbGciOiJIUzI1NiIs...）
    """
    to_encode = data.copy()

    # 设置过期时间
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """解码并验证 JWT Token

    自动验证：
    - 签名是否有效（使用 SECRET_KEY）
    - 是否过期（exp 字段）
    - 算法是否匹配（HS256）

    Args:
        token: JWT 字符串

    Returns:
        payload dict（成功） / None（无效或过期）
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError:
        return None


# ============================================================
# FastAPI 依赖注入：获取当前用户
# ============================================================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI 依赖：从 JWT 还原当前用户

    调用链：
    Request → Authorization Header
           → OAuth2PasswordBearer 提取 token
           → decode_access_token 验证 token
           → query users 表
           → return User ORM obj

    Args:
        token: 自动从 Authorization: Bearer <token> 提取
        db: 数据库会话（自动注入）

    Returns:
        User ORM 对象

    Raises:
        HTTPException 401: token 无效 / 用户不存在 / 用户被禁用
    """
    # Step 1: 解码 token
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Step 2: 提取 user_id
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌中缺少用户标识",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Step 3: 查询用户
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Step 4: 检查用户状态
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户已被禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# ============================================================
# 可选依赖：获取当前用户 ID（简化 service 层调用）
# ============================================================

def get_current_user_id(current_user: User = Depends(get_current_user)) -> str:
    """快速获取当前用户 ID（service 层用）

    避免每个 service 方法都 import User 模型。

    Args:
        current_user: 由 get_current_user 注入

    Returns:
        用户 ID 字符串
    """
    return current_user.id
