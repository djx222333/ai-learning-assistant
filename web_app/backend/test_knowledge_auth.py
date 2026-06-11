"""Knowledge 模块 JWT 用户隔离测试

测试内容：
1. 用户 A 上传文档 -> 成功
2. 用户 A 查看文件列表 -> 看到自己的文档
3. 用户 B 查看文件列表 -> 看不到 A 的文档
4. 用户 B 删除 A 的文档 -> 404
5. 用户 A 删除自己的文档 -> 200
6. 无 Token 上传 -> 401
7. 无 Token 查看列表 -> 401
8. 无 Token 删除 -> 401

运行方式：
  cd web_app/backend
  python -m pytest test_knowledge_auth.py -v --tb=short
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

os.environ["SECRET_KEY"] = "test-secret-key-knowledge"
os.environ["DATABASE_URL"] = "sqlite:///./test_knowledge_auth.db"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "15"

import pytest
from fastapi.testclient import TestClient
from app.database import init_db, drop_db
from app.main import app

client = TestClient(app)
AUTH = "/api/v1/auth"
BASE = "/api/v1/knowledge"


@pytest.fixture(autouse=True)
def setup_db():
    """每个测试前重建数据库"""
    drop_db()
    init_db()
    yield
    drop_db()


def register_user(username: str, password: str = "test123"):
    """注册并登录，返回 (user_id, token)"""
    client.post(f"{AUTH}/register", json={
        "username": username,
        "password": password,
    })
    resp = client.post(f"{AUTH}/login", data={
        "username": username,
        "password": password,
    })
    data = resp.json()
    return data["user"]["id"], data["access_token"]


def create_valid_pdf(tmp_path: str, text: str = "Hello World"):
    """用 pymupdf 创建真实的最小 PDF 文件"""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text, fontsize=12)
    doc.save(tmp_path)
    doc.close()


class TestKnowledgeUserIsolation:
    """知识库用户隔离测试"""

    @pytest.fixture(autouse=True)
    def seed_users(self):
        """创建用户 A 和用户 B"""
        self.uid_a, self.token_a = register_user("user_a")
        self.uid_b, self.token_b = register_user("user_b")

    def _upload(self, token: str, filename: str = "test.pdf") -> dict:
        """辅助：上传一个真实 PDF"""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            tmp_path = f.name
        try:
            create_valid_pdf(tmp_path, f"Content from {filename}")
            with open(tmp_path, "rb") as f:
                resp = client.post(
                    f"{BASE}/upload",
                    files={"file": (filename, f, "application/pdf")},
                    headers={"Authorization": f"Bearer {token}"},
                )
            return resp
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    # ===== 上传 =====

    def test_upload_without_token(self):
        """无 Token 上传应返回 401"""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            tmp_path = f.name
        try:
            create_valid_pdf(tmp_path)
            with open(tmp_path, "rb") as f:
                resp = client.post(
                    f"{BASE}/upload",
                    files={"file": ("test.pdf", f, "application/pdf")},
                )
            assert resp.status_code == 401
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_upload_as_user_a(self):
        """用户 A 上传应成功"""
        resp = self._upload(self.token_a)
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["filename"] == "test.pdf"
        assert data["index_status"] == "ready"

    # ===== 文件列表 =====

    def test_list_files_without_token(self):
        """无 Token 查看列表应返回 401"""
        resp = client.get(f"{BASE}/files")
        assert resp.status_code == 401

    def test_user_b_cannot_see_user_a_files(self):
        """用户 B 看不到用户 A 的文档"""
        self._upload(self.token_a, "a_doc.pdf")
        resp = client.get(
            f"{BASE}/files",
            headers={"Authorization": f"Bearer {self.token_b}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_user_a_sees_own_files(self):
        """用户 A 能看到自己的文档"""
        self._upload(self.token_a, "my_doc.pdf")
        resp = client.get(
            f"{BASE}/files",
            headers={"Authorization": f"Bearer {self.token_a}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["filename"] == "my_doc.pdf"

    # ===== 删除 =====

    def test_delete_without_token(self):
        """无 Token 删除应返回 401"""
        resp = client.delete(f"{BASE}/some-id")
        assert resp.status_code == 401

    def test_user_b_cannot_delete_user_a_document(self):
        """用户 B 不能删除用户 A 的文档"""
        upload_resp = self._upload(self.token_a, "secret.pdf")
        doc_id = upload_resp.json()["id"]
        resp = client.delete(
            f"{BASE}/{doc_id}",
            headers={"Authorization": f"Bearer {self.token_b}"},
        )
        assert resp.status_code == 404

    def test_user_a_can_delete_own_document(self):
        """用户 A 可以删除自己的文档"""
        upload_resp = self._upload(self.token_a, "my_doc.pdf")
        doc_id = upload_resp.json()["id"]
        resp = client.delete(
            f"{BASE}/{doc_id}",
            headers={"Authorization": f"Bearer {self.token_a}"},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "deleted"

    def test_delete_nonexistent_returns_404(self):
        """删除不存在的文档应返回 404"""
        resp = client.delete(
            f"{BASE}/nonexistent-id",
            headers={"Authorization": f"Bearer {self.token_a}"},
        )
        assert resp.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])