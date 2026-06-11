"""api/v1/auth.py 集成测试

测试内容：
1. POST /register — 注册成功 / 重复用户名 409 / 重复邮箱 409
2. POST /login — 登录成功 / 密码错误 401 / 用户不存在 401
3. GET /me — 有效 Token / 无效 Token 401 / 过期 Token 401
4. 完整流程：注册 → 登录 → 访问 /me

运行方式：
  cd web_app/backend
  python -m pytest test_auth_api.py -v --tb=short
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

os.environ["SECRET_KEY"] = "test-secret-key-for-api-tests"
os.environ["DATABASE_URL"] = "sqlite:///./test_auth_api.db"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "15"

import pytest
from fastapi.testclient import TestClient
from app.database import init_db, drop_db, SessionLocal
from app.main import app

client = TestClient(app)

BASE = "/api/v1/auth"


@pytest.fixture(autouse=True)
def setup_db():
    """每个测试前重建数据库"""
    drop_db()
    init_db()
    yield
    drop_db()


class TestRegister:
    """POST /api/v1/auth/register"""

    def test_register_success(self):
        """注册成功应返回 201 + 用户信息"""
        resp = client.post(f"{BASE}/register", json={
            "username": "testuser",
            "password": "123456",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "testuser"
        assert "id" in data
        assert data["is_active"] is True
        assert "created_at" in data
        # 密码不应返回
        assert "password" not in data

    def test_register_with_email(self):
        """注册时可选填邮箱"""
        resp = client.post(f"{BASE}/register", json={
            "username": "user_with_email",
            "password": "123456",
            "email": "test@example.com",
        })
        assert resp.status_code == 201
        assert resp.json()["email"] == "test@example.com"

    def test_register_duplicate_username(self):
        """重复用户名应返回 409"""
        client.post(f"{BASE}/register", json={"username": "dup", "password": "123456"})
        resp = client.post(f"{BASE}/register", json={"username": "dup", "password": "654321"})
        assert resp.status_code == 409
        assert resp.json()["detail"] == "用户名已存在"

    def test_register_duplicate_email(self):
        """重复邮箱应返回 409"""
        client.post(f"{BASE}/register", json={
            "username": "user1", "password": "123456", "email": "same@e.com",
        })
        resp = client.post(f"{BASE}/register", json={
            "username": "user2", "password": "123456", "email": "same@e.com",
        })
        assert resp.status_code == 409
        assert resp.json()["detail"] == "邮箱已被注册"

    def test_register_username_too_short(self):
        """用户名太短应返回 422"""
        resp = client.post(f"{BASE}/register", json={"username": "a", "password": "123456"})
        assert resp.status_code == 422

    def test_register_password_too_short(self):
        """密码太短应返回 422"""
        resp = client.post(f"{BASE}/register", json={"username": "valid", "password": "12345"})
        assert resp.status_code == 422


class TestLogin:
    """POST /api/v1/auth/login"""

    @pytest.fixture(autouse=True)
    def seed_user(self):
        """每个测试前注册一个用户"""
        client.post(f"{BASE}/register", json={"username": "logintest", "password": "pass123"})

    def test_login_success(self):
        """正确密码应返回 Token"""
        resp = client.post(f"{BASE}/login", data={
            "username": "logintest",
            "password": "pass123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "logintest"
        # Token 应为 3 段 JWT
        assert len(data["access_token"].split(".")) == 3

    def test_login_wrong_password(self):
        """错误密码应返回 401"""
        resp = client.post(f"{BASE}/login", data={
            "username": "logintest",
            "password": "wrongpass",
        })
        assert resp.status_code == 401
        assert resp.json()["detail"] == "用户名或密码错误"

    def test_login_nonexistent_user(self):
        """不存在的用户应返回 401"""
        resp = client.post(f"{BASE}/login", data={
            "username": "nobody",
            "password": "pass123",
        })
        assert resp.status_code == 401

    def test_login_uses_form_data(self):
        """登录应使用 form-data（兼容 Swagger Authorize）"""
        resp = client.post(
            f"{BASE}/login",
            data={"username": "logintest", "password": "pass123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200


class TestGetMe:
    """GET /api/v1/auth/me"""

    @pytest.fixture(autouse=True)
    def seed_and_login(self):
        """注册并登录，保存 token"""
        client.post(f"{BASE}/register", json={"username": "metest", "password": "pass123"})
        resp = client.post(f"{BASE}/login", data={"username": "metest", "password": "pass123"})
        self.token = resp.json()["access_token"]

    def test_get_me_success(self):
        """有效 Token 应返回用户信息"""
        resp = client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {self.token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "metest"
        assert data["is_active"] is True
        assert "created_at" in data

    def test_get_me_no_token(self):
        """无 Token 应返回 401"""
        resp = client.get(f"{BASE}/me")
        assert resp.status_code == 401
        assert "detail" in resp.json()

    def test_get_me_invalid_token(self):
        """无效 Token 应返回 401"""
        resp = client.get(f"{BASE}/me", headers={"Authorization": "Bearer invalid-token"})
        assert resp.status_code == 401

    def test_get_me_expired_token(self):
        """过期 Token 应返回 401"""
        from app.services.auth_service import create_access_token
        from datetime import timedelta

        expired_token = create_access_token(
            {"sub": "any-id"},
            expires_delta=timedelta(seconds=-1),
        )
        resp = client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {expired_token}"})
        assert resp.status_code == 401


class TestFullFlow:
    """完整流程测试：注册 → 登录 → 访问受保护资源"""

    def test_full_auth_flow(self):
        """端到端认证流程"""
        # Step 1: 注册
        reg = client.post(f"{BASE}/register", json={
            "username": "flowuser",
            "password": "mypassword",
        })
        assert reg.status_code == 201
        user_id = reg.json()["id"]

        # Step 2: 登录
        login = client.post(f"{BASE}/login", data={
            "username": "flowuser",
            "password": "mypassword",
        })
        assert login.status_code == 200
        token = login.json()["access_token"]
        assert login.json()["user"]["id"] == user_id

        # Step 3: 访问 /me
        me = client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["id"] == user_id


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
