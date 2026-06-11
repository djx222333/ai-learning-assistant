# -*- coding: utf-8 -*-
"""认证 API 路由

API 清单：
  POST /api/v1/auth/register    — 用户注册
  POST /api/v1/auth/login       — 用户登录（返回 JWT）
  GET  /api/v1/auth/me          — 获取当前用户信息

设计原则：
1. 注册和登录使用 Pydantic 请求体（JSON），login 额外支持 OAuth2 form
2. 密码只在注册时接收，永不返回
3. 所有错误使用统一 HTTPException 格式
4. Swagger "Authorize" 按钮通过 OAuth2PasswordRequestForm 兼容
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.models import User
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])


# ============================================================
# Pydantic 数据模型
# ============================================================

class RegisterRequest(BaseModel):
    """注册请求体"""
    username: str = Field(
        ..., min_length=2, max_length=64,
        description="用户名，唯一",
        examples=["zhangsan"],
    )
    password: str = Field(
        ..., min_length=6, max_length=128,
        description="密码（明文，服务端用 bcrypt 加密存储）",
        examples=["123456"],
    )
    email: Optional[str] = Field(
        None, max_length=128,
        description="邮箱（可选）",
        examples=["zhangsan@example.com"],
    )


class UserResponse(BaseModel):
    """用户信息响应（不包含密码）"""
    id: str = Field(..., description="用户 UUID")
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    is_active: bool = Field(True, description="账户是否激活")
    created_at: str = Field(..., description="注册时间 (ISO8601)")

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    """登录成功响应"""
    access_token: str = Field(..., description="JWT Access Token")
    token_type: str = Field("bearer", description="Token 类型")
    user: UserResponse = Field(..., description="用户基本信息")

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIs...",
                "token_type": "bearer",
                "user": {
                    "id": "uuid-xxx",
                    "username": "zhangsan",
                    "email": "zhangsan@example.com",
                    "is_active": True,
                    "created_at": "2026-06-11T12:00:00Z",
                },
            }
        }
    }


class ErrorResponse(BaseModel):
    """统一错误响应"""
    detail: str = Field(..., description="错误描述")


# ============================================================
# 注册
# ============================================================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
    description="创建新用户账号，密码使用 bcrypt 加密存储",
    responses={
        201: {"description": "注册成功，返回用户信息"},
        409: {"description": "用户名或邮箱已存在", "model": ErrorResponse},
    },
)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    """注册新用户

    流程：
    1. 校验用户名是否已存在（唯一约束）
    2. bcrypt 哈希密码
    3. INSERT users 表
    4. 返回用户信息（不包含密码）

    Raises:
        HTTPException 409: 用户名或邮箱已被注册
    """
    # 检查用户名是否重复
    existing = db.query(User).filter(User.username == request.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已存在",
        )

    # 如果有邮箱，检查邮箱是否重复
    if request.email:
        existing_email = db.query(User).filter(User.email == request.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="邮箱已被注册",
            )

    # 创建用户
    now = datetime.now(timezone.utc)
    user = User(
        username=request.username,
        email=request.email,
        hashed_password=hash_password(request.password),
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


# ============================================================
# 登录
# ============================================================

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="用户登录",
    description="使用用户名和密码登录，返回 JWT Access Token",
    responses={
        200: {"description": "登录成功，返回 Token"},
        401: {"description": "用户名或密码错误", "model": ErrorResponse},
    },
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """用户登录

    同时支持：
    - Swagger UI "Authorize" 按钮（OAuth2PasswordRequestForm）
    - 直接 POST form-data {username, password}

    流程：
    1. 查询用户（by username）
    2. bcrypt 校验密码
    3. 签发 JWT（payload: {sub: user_id}）
    4. 返回 {access_token, token_type, user}

    Raises:
        HTTPException 401: 用户名或密码错误（不区分具体哪个错）
    """
    # 查询用户
    user = db.query(User).filter(User.username == form_data.username).first()

    # 校验：不区分"用户不存在"和"密码错误"（防止枚举）
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查账户状态
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账户已被禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 签发 JWT
    access_token = create_access_token(data={"sub": user.id})

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else "",
        ),
    )


# ============================================================
# 获取当前用户
# ============================================================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="获取当前用户",
    description="返回当前登录用户的详细信息（需携带 JWT Token）",
    responses={
        200: {"description": "返回用户信息"},
        401: {"description": "未认证或 Token 无效", "model": ErrorResponse},
    },
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    """获取当前登录用户信息

    依赖 get_current_user（自动从 Authorization Header 提取 JWT）

    Returns:
        用户信息（id, username, email, is_active, created_at）
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat() if current_user.created_at else "",
    )
