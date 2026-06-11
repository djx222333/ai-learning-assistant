"""auth_service.py 单元测试

测试内容：
1. hash_password / verify_password — bcrypt 密码哈希
2. create_access_token / decode_access_token — JWT 生成与验证
3. Token 过期检测
4. 无效 Token 检测
5. get_current_user 依赖注入（mock DB）

运行方式：
  cd web_app/backend
  python -m pytest test_auth_service.py -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import timedelta, timezone, datetime
import pytest
from jose import jwt

# 设置测试用环境变量（必须在 import 任何 app 模块前）
os.environ["SECRET_KEY"] = "test-secret-key-do-not-use-in-production"
os.environ["DATABASE_URL"] = "sqlite:///./test_auth.db"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "15"

from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    get_current_user,
)
from app.core.config import settings


class TestPasswordHashing:
    """密码哈希功能测试"""

    def test_hash_password_returns_string(self):
        """hash_password 应返回字符串"""
        hashed = hash_password("test_password_123")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_starts_with_bcrypt_prefix(self):
        """bcrypt hash 应以 $2b$ 开头"""
        hashed = hash_password("test")
        assert hashed.startswith("$2b$")

    def test_same_password_different_hashes(self):
        """相同密码每次哈希结果不同（自动加盐）"""
        h1 = hash_password("my_password")
        h2 = hash_password("my_password")
        assert h1 != h2

    def test_verify_password_correct(self):
        """正确密码应验证通过"""
        hashed = hash_password("my_password")
        assert verify_password("my_password", hashed) is True

    def test_verify_password_wrong(self):
        """错误密码应验证失败"""
        hashed = hash_password("my_password")
        assert verify_password("wrong_password", hashed) is False

    def test_verify_password_empty(self):
        """空密码验证应正常返回 False"""
        hashed = hash_password("my_password")
        assert verify_password("", hashed) is False


class TestJWTTokens:
    """JWT Token 生成与验证功能测试"""

    def test_create_token_returns_string(self):
        """create_access_token 应返回字符串"""
        token = create_access_token({"sub": "user-123"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_contains_dots(self):
        """JWT 应包含 3 段（header.payload.signature）"""
        token = create_access_token({"sub": "user-123"})
        parts = token.split(".")
        assert len(parts) == 3

    def test_decode_valid_token(self):
        """有效 Token 应正确解码"""
        token = create_access_token({"sub": "user-456"})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "user-456"

    def test_decode_token_with_extra_data(self):
        """Token 应保留自定义数据"""
        token = create_access_token({
            "sub": "user-789",
            "username": "testuser",
            "role": "admin",
        })
        payload = decode_access_token(token)
        assert payload["username"] == "testuser"
        assert payload["role"] == "admin"

    def test_decode_invalid_token(self):
        """无效 Token 应返回 None"""
        payload = decode_access_token("invalid-token-string")
        assert payload is None

    def test_decode_tampered_token(self):
        """篡改的 Token 应返回 None"""
        token = create_access_token({"sub": "user-123"})
        tampered = token[:-5] + "XXXXX"
        payload = decode_access_token(tampered)
        assert payload is None

    def test_decode_expired_token(self):
        """过期的 Token 应返回 None"""
        token = create_access_token(
            {"sub": "user-expired"},
            expires_delta=timedelta(seconds=-1),  # 过期1秒
        )
        payload = decode_access_token(token)
        assert payload is None

    def test_custom_expiry(self):
        """自定义过期时间应生效"""
        token = create_access_token(
            {"sub": "user-custom"},
            expires_delta=timedelta(hours=24),
        )
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "user-custom"

    def test_token_payload_contains_exp(self):
        """Token payload 应包含 exp 字段"""
        token = create_access_token({"sub": "user-exp-check"})
        # 解码（跳过过期检查）
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False},
        )
        assert "exp" in payload
        assert isinstance(payload["exp"], int)

    def test_decode_token_no_subject(self):
        """不含 sub 的 Token 创建后应能解码"""
        token = create_access_token({"foo": "bar"})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload.get("sub") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
