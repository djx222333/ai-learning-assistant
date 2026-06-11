"""Conversation History API 测试

测试策略：避免调用 LLM，直接写数据库创建测试数据。
使用 chat_service._get_or_create_conversation() 创建会话。

运行方式：
  cd web_app/backend
  python -m pytest test_conversations.py -v --tb=short
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

os.environ["SECRET_KEY"] = "test-secret-conv-key"
os.environ["DATABASE_URL"] = "sqlite:///./test_conversations.db"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "15"

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from app.database import init_db, drop_db, SessionLocal
from app.models import Conversation, Message
from app.main import app

client = TestClient(app)
AUTH = "/api/v1/auth"
BASE = "/api/v1/conversations"


@pytest.fixture(autouse=True)
def setup_db():
    drop_db()
    init_db()
    yield
    drop_db()


def register_user(username: str, password: str = "test123"):
    """注册并登录，返回 (user_id, token)"""
    client.post(f"{AUTH}/register", json={"username": username, "password": password})
    resp = client.post(f"{AUTH}/login", data={"username": username, "password": password})
    return resp.json()["user"]["id"], resp.json()["access_token"]


def create_conversation(user_id: str, session_id: str, title: str = "测试会话"):
    """直接写数据库创建会话 + 2 条消息"""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        conv = Conversation(
            user_id=user_id,
            session_id=session_id,
            title=title,
            message_count=2,
            created_at=now,
            updated_at=now,
        )
        db.add(conv)
        db.flush()

        user_msg = Message(
            conversation_id=conv.id,
            role="user",
            content=f"测试问题 {session_id}",
            created_at=now,
        )
        db.add(user_msg)

        ai_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content=f"测试回答 {session_id}",
            agent_type="code",
            agent_name="Code Agent",
            citations=None,
            created_at=now,
        )
        db.add(ai_msg)
        db.commit()
        return conv.id
    finally:
        db.close()


class TestConversationHistory:
    """对话历史 API 测试"""

    @pytest.fixture(autouse=True)
    def seed(self):
        self.uid_a, self.token_a = register_user("user_a")
        self.uid_b, self.token_b = register_user("user_b")

    # ===== 列表 =====

    def test_list_empty(self):
        """新用户应返回空列表"""
        resp = client.get(BASE, headers={"Authorization": f"Bearer {self.token_a}"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert resp.json()["items"] == []

    def test_list_after_conversation(self):
        """有会话后列表应有 1 条"""
        create_conversation(self.uid_a, "s1")
        resp = client.get(BASE, headers={"Authorization": f"Bearer {self.token_a}"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["session_id"] == "s1"

    def test_list_without_token(self):
        """无 Token 应返回 401"""
        resp = client.get(BASE)
        assert resp.status_code == 401

    def test_list_returns_metadata(self):
        """列表返回完整元数据"""
        create_conversation(self.uid_a, "s_meta")
        resp = client.get(BASE, headers={"Authorization": f"Bearer {self.token_a}"})
        item = resp.json()["items"][0]
        assert "id" in item
        assert "session_id" in item
        assert "title" in item
        assert "message_count" in item
        assert "last_message" in item
        assert "created_at" in item
        assert "updated_at" in item

    # ===== 详情 =====

    def test_get_detail(self):
        """获取会话详情"""
        cid = create_conversation(self.uid_a, "s2")
        resp = client.get(f"{BASE}/{cid}", headers={"Authorization": f"Bearer {self.token_a}"})
        assert resp.status_code == 200
        assert resp.json()["id"] == cid
        assert resp.json()["message_count"] == 2

    def test_get_detail_cross_user(self):
        """用户 B 不能查看用户 A 的会话"""
        cid = create_conversation(self.uid_a, "s3")
        resp = client.get(f"{BASE}/{cid}", headers={"Authorization": f"Bearer {self.token_b}"})
        assert resp.status_code == 404

    def test_get_detail_nonexistent(self):
        """不存在的会话应返回 404"""
        resp = client.get(f"{BASE}/nonexistent", headers={"Authorization": f"Bearer {self.token_a}"})
        assert resp.status_code == 404

    # ===== 消息 =====

    def test_get_messages(self):
        """获取消息应返回 user + assistant"""
        cid = create_conversation(self.uid_a, "s4")
        resp = client.get(f"{BASE}/{cid}/messages", headers={"Authorization": f"Bearer {self.token_a}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["items"][0]["role"] == "user"
        assert data["items"][1]["role"] == "assistant"

    def test_get_messages_contains_agent_info(self):
        """消息应包含 agent_type, agent_name, citations"""
        cid = create_conversation(self.uid_a, "s_agent")
        resp = client.get(f"{BASE}/{cid}/messages", headers={"Authorization": f"Bearer {self.token_a}"})
        ai_msg = resp.json()["items"][1]
        assert ai_msg["agent_type"] == "code"
        assert ai_msg["agent_name"] == "Code Agent"

    def test_get_messages_cross_user(self):
        """用户 B 不能查看用户 A 的消息"""
        cid = create_conversation(self.uid_a, "s5")
        resp = client.get(f"{BASE}/{cid}/messages", headers={"Authorization": f"Bearer {self.token_b}"})
        assert resp.status_code == 404

    # ===== 删除 =====

    def test_delete_conversation(self):
        """删除会话应成功且级联删除消息"""
        cid = create_conversation(self.uid_a, "s6")
        resp = client.delete(f"{BASE}/{cid}", headers={"Authorization": f"Bearer {self.token_a}"})
        assert resp.status_code == 200
        assert resp.json()["message"] == "deleted"
        # 确认列表为空
        resp2 = client.get(BASE, headers={"Authorization": f"Bearer {self.token_a}"})
        assert resp2.json()["total"] == 0

    def test_delete_cross_user(self):
        """用户 B 不能删除用户 A 的会话"""
        cid = create_conversation(self.uid_a, "s7")
        resp = client.delete(f"{BASE}/{cid}", headers={"Authorization": f"Bearer {self.token_b}"})
        assert resp.status_code == 404

    def test_delete_nonexistent(self):
        """删除不存在的会话返回 404"""
        resp = client.delete(f"{BASE}/nonexistent", headers={"Authorization": f"Bearer {self.token_a}"})
        assert resp.status_code == 404

    # ===== 排序 =====

    def test_list_ordered_by_updated_at_desc(self):
        """列表应按 updated_at 倒序"""
        from datetime import timedelta
        create_conversation(self.uid_a, "s_old")
        import time; time.sleep(0.1)
        create_conversation(self.uid_a, "s_new")

        resp = client.get(BASE + "?limit=10", headers={"Authorization": f"Bearer {self.token_a}"})
        items = resp.json()["items"]
        assert items[0]["session_id"] == "s_new"
        assert items[1]["session_id"] == "s_old"

    # ===== 分页 =====

    def test_list_pagination(self):
        """分页应正确返回指定条数"""
        for i in range(5):
            create_conversation(self.uid_a, f"s_pg_{i}")
        page1 = client.get(BASE + "?offset=0&limit=2", headers={"Authorization": f"Bearer {self.token_a}"})
        assert page1.json()["total"] == 5
        assert len(page1.json()["items"]) == 2
        page2 = client.get(BASE + "?offset=2&limit=2", headers={"Authorization": f"Bearer {self.token_a}"})
        assert len(page2.json()["items"]) == 2

    # ===== 消息分页 =====

    def test_messages_pagination(self):
        """消息列表分页应正确"""
        cid = create_conversation(self.uid_a, "s_msg")
        # 再额外加几条消息
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            for i in range(4):
                msg = Message(conversation_id=cid, role="user" if i % 2 == 0 else "assistant",
                              content=f"额外{i}", created_at=now)
                db.add(msg)
            db.commit()
            db.query(Conversation).filter(Conversation.id == cid).update({"message_count": 6})
            db.commit()
        finally:
            db.close()

        resp = client.get(f"{BASE}/{cid}/messages?offset=0&limit=2",
                          headers={"Authorization": f"Bearer {self.token_a}"})
        assert resp.json()["total"] >= 2
        assert len(resp.json()["items"]) == 2

    # ===== 用户隔离 =====

    def test_user_isolation(self):
        """用户隔离：A 和 B 互不可见"""
        create_conversation(self.uid_a, "s_a")
        create_conversation(self.uid_b, "s_b")
        list_a = client.get(BASE, headers={"Authorization": f"Bearer {self.token_a}"})
        list_b = client.get(BASE, headers={"Authorization": f"Bearer {self.token_b}"})
        assert list_a.json()["total"] == 1
        assert list_b.json()["total"] == 1
        assert list_a.json()["items"][0]["session_id"] == "s_a"
        assert list_b.json()["items"][0]["session_id"] == "s_b"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])