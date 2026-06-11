import requests, json, sys, os

# 设置 UTF-8 输出
sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://localhost:8000"

def test_chat(message, session_id="test-session-1"):
    resp = requests.post(
        f"{BASE}/api/v1/chat",
        json={"message": message, "session_id": session_id},
        timeout=60,
    )
    return resp.json()

def test_list_files():
    resp = requests.get(f"{BASE}/api/v1/knowledge/files")
    return resp.json()

def test_upload(pdf_path, filename="test.pdf"):
    with open(pdf_path, "rb") as f:
        resp = requests.post(
            f"{BASE}/api/v1/knowledge/upload",
            files={"file": (filename, f, "application/pdf")},
            timeout=120,
        )
    return resp.json()

def test_delete(file_id):
    resp = requests.delete(f"{BASE}/api/v1/knowledge/{file_id}")
    return resp.status_code, resp.json()

passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  [PASS] {name}")
        passed += 1
    else:
        print(f"  [FAIL] {name} {detail}")
        failed += 1

def main():
    global passed, failed
    pdf_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "uploads", "test_python_lists.pdf"
    ))

    # ---- Test 1 ----
    print("=" * 60)
    print("TEST 1: 无知识库聊天（降级测试）")
    print("=" * 60)
    data = test_chat("Python 列表是什么？", "test-p0-006")
    check("Citations 为空", len(data["citations"]) == 0,
          f"Got citations: {data['citations']}")
    check("Agent 类型有效", data["agent_type"] in ["code", "english", "career", "search", "research", "rag", "planner"],
          f"Unknown: {data['agent_type']}")
    print()

    # ---- Test 2 ----
    print("=" * 60)
    print("TEST 2: 知识库文件列表（应为空）")
    print("=" * 60)
    files = test_list_files()
    check("文件列表返回列表", isinstance(files, list))
    check("文件数量为 0", len(files) == 0, f"Got {len(files)} files")
    print()

    # ---- Test 3 ----
    if not os.path.exists(pdf_path):
        print(f"SKIP Test 3-7: Test PDF not found at {pdf_path}")
        return

    print("=" * 60)
    print("TEST 3: 上传 PDF")
    print("=" * 60)
    data3 = test_upload(pdf_path, "test_python_lists.pdf")
    check("索引状态有效", data3["index_status"] in ["processing", "ready", "failed"],
          f"Status: {data3['index_status']}")
    check("文件名正确", data3["filename"] == "test_python_lists.pdf",
          f"Got: {data3['filename']}")
    check("文本块 > 0", data3["chunk_count"] > 0,
          f"Chunks: {data3['chunk_count']}")
    print(f"  Details: {data3['chunk_count']} chunks, {data3['page_count']} pages, status={data3['index_status']}")
    test_doc_id = data3["id"]
    print()

    # ---- Test 4 ----
    print("=" * 60)
    print("TEST 4: 知识库问答（含 citation）")
    print("=" * 60)
    data4 = test_chat("Python 列表有哪些方法？", "test-p0-006-rag")
    check("有 citations 返回", len(data4["citations"]) > 0,
          f"Got {len(data4['citations'])} citations")
    check("Agent 类型有效", data4["agent_type"] in ["code", "english", "career", "search", "research", "rag", "planner"])
    print(f"  Agent: {data4['agent_name']} ({data4['agent_type']})")
    for c in data4.get("citations", []):
        check(f"Citation 有 document_name", "document_name" in c and c["document_name"],
              f"Missing document_name")
        check(f"Citation 有 chunk_id", "chunk_id" in c,
              f"Missing chunk_id")
        check(f"Citation 有 relevance_score", "relevance_score" in c,
              f"Missing relevance_score")
        print(f"  - doc={c['document_name']}, chunk_id={c['chunk_id']}, score={c['relevance_score']}")
    print()

    # ---- Test 5 ----
    print("=" * 60)
    print("TEST 5: 删除文件")
    print("=" * 60)
    status, data5 = test_delete(test_doc_id)
    check("删除返回 200", status == 200, f"Status: {status}")
    check("删除消息正确", data5.get("message") == "deleted",
          f"Got: {data5}")
    print()

    # ---- Test 6 ----
    print("=" * 60)
    print("TEST 6: 验证删除后文件列表")
    print("=" * 60)
    files_after = test_list_files()
    deleted = all(f["id"] != test_doc_id for f in files_after)
    check("文档已从列表中移除", deleted)
    print()

    # ---- Test 7 ----
    print("=" * 60)
    print("TEST 7: 删除后提问（应降级）")
    print("=" * 60)
    data7 = test_chat("Python 是什么？", "test-p0-006-final")
    check("删除后 citations 为空", len(data7["citations"]) == 0,
          f"Got {len(data7['citations'])} citations")
    print()

    # ---- Summary ----
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
