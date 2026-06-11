import requests, json, sys, os

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://localhost:8000"

def chat(msg, sid="test-pg-1"):
    r = requests.post(f"{BASE}/api/v1/chat", json={"message": msg, "session_id": sid}, timeout=60)
    return r.json()

def files():
    r = requests.get(f"{BASE}/api/v1/knowledge/files")
    return r.json()

def upload(pdf_path, fname="test.pdf"):
    with open(pdf_path, "rb") as f:
        r = requests.post(f"{BASE}/api/v1/knowledge/upload", files={"file": (fname, f, "application/pdf")}, timeout=120)
    return r.json()

def delete(doc_id):
    r = requests.delete(f"{BASE}/api/v1/knowledge/{doc_id}")
    return r.status_code, r.json()

def check_db(sql):
    """直接查询 SQLite 数据库验证数据"""
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "app.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(sql)
    rows = cursor.fetchall()
    conn.close()
    return rows

passed = 0
failed = 0

def ok(name, cond, detail=""):
    global passed, failed
    if cond:
        print(f"  [PASS] {name}")
        passed += 1
    else:
        print(f"  [FAIL] {name} {detail}")
        failed += 1

def main():
    global passed, failed
    pdf = os.path.abspath(os.path.join(os.path.dirname(__file__), "uploads", "test_python_lists.pdf"))

    # ---- Test 1: 无知识库 ----
    print("=" * 60)
    print("TEST 1: 无知识库聊天")
    print("=" * 60)
    d = chat("Hello", "test-db-1")
    ok("citations 为空", len(d.get("citations", [])) == 0)
    ok("agent 类型有效", d["agent_type"] in ("code","english","career","search","research","rag","planner"))
    print()

    # ---- Test 2: 验证消息已持久化 ----
    print("=" * 60)
    print("TEST 2: 消息持久化验证")
    print("=" * 60)
    rows = check_db("SELECT count(*) FROM messages")
    ok("messages 表有数据", rows[0][0] > 0, f"count={rows[0][0]}")
    rows2 = check_db("SELECT count(*) FROM conversations")
    ok("conversations 表有数据", rows2[0][0] > 0)
    rows3 = check_db("SELECT role, agent_type FROM messages ORDER BY created_at LIMIT 2")
    ok("user 消息已保存", rows3[0][0] == "user")
    ok("assistant 消息已保存", len(rows3) > 1 and rows3[1][0] == "assistant")
    print()

    # ---- Test 3: 上传 PDF ----
    if not os.path.exists(pdf):
        print(f"SKIP Tests 3-9: PDF not found")
        return

    print("=" * 60)
    print("TEST 3: 上传 PDF")
    print("=" * 60)
    d3 = upload(pdf, "test_python_lists.pdf")
    ok("索引成功", d3["index_status"] == "ready", f"status={d3['index_status']}")
    ok("chunk > 0", d3["chunk_count"] > 0)
    print(f"  chunks={d3['chunk_count']}, pages={d3['page_count']}")
    doc_id = d3["id"]
    print()

    # ---- Test 4: 验证文档在数据库中 ----
    print("=" * 60)
    print("TEST 4: 数据库文档记录验证")
    print("=" * 60)
    rows = check_db(f"SELECT id, filename, index_status, chunk_count FROM documents WHERE id='{doc_id}'")
    ok("文档记录存在", len(rows) > 0)
    ok("文件名正确", rows[0][1] == "test_python_lists.pdf")
    ok("索引状态正确", rows[0][2] == "ready")
    print(f"  doc_id={doc_id}")
    print()

    # ---- Test 5: 验证 Chunk 在数据库中 ----
    print("=" * 60)
    print("TEST 5: 数据库 chunk 记录验证")
    print("=" * 60)
    rows = check_db(f"SELECT count(*) FROM chunks WHERE document_id='{doc_id}'")
    ok("chunk 记录存在", rows[0][0] > 0, f"count={rows[0][0]}")
    print()

    # ---- Test 6: 知识库问答 ----
    print("=" * 60)
    print("TEST 6: 知识库问答")
    print("=" * 60)
    d6 = chat("Python 列表有哪些方法？", "test-db-rag")
    ok("有 citations", len(d6.get("citations", [])) > 0)
    for c in d6.get("citations", []):
        ok("document_name 真实", c["document_name"] == "test_python_lists.pdf")
        ok("chunk_id 存在", "chunk_id" in c)
        ok("relevance_score 存在", "relevance_score" in c)
    print()

    # ---- Test 7: 删除后验证 ----
    print("=" * 60)
    print("TEST 7: 删除文件")
    print("=" * 60)
    status, d7 = delete(doc_id)
    ok("删除返回 200", status == 200)
    files_after = files()
    ok("文档从列表移除", all(f["id"] != doc_id for f in files_after))
    print()

    # ---- Test 8: 验证删除后数据库同步 ----
    print("=" * 60)
    print("TEST 8: 删除后数据库验证")
    print("=" * 60)
    rows = check_db(f"SELECT count(*) FROM documents WHERE id='{doc_id}'")
    ok("文档已从 documents 表删除", rows[0][0] == 0)
    rows2 = check_db(f"SELECT count(*) FROM chunks WHERE document_id='{doc_id}'")
    ok("chunk 已从 chunks 表删除", rows2[0][0] == 0)
    print()

    # ---- Test 9: 删除后聊天降级 ----
    print("=" * 60)
    print("TEST 9: 删除后降级")
    print("=" * 60)
    d9 = chat("Python 是什么？", "test-db-final")
    ok("citations 为空", len(d9.get("citations", [])) == 0)
    print()

    # ---- Summary ----
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
