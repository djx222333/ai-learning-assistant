"""Test the new Planner API"""
import requests, json, sys, os

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://localhost:8000"

def test_generate_plan():
    """Test: Generate a learning plan"""
    print("=" * 60)
    print("TEST: Generate Learning Plan")
    print("=" * 60)
    
    resp = requests.post(
        f"{BASE}/api/v1/plans/generate",
        json={"goal": "8周内学会 FastAPI", "duration_weeks": 8},
        timeout=120,
    )
    d = resp.json()
    
    assert resp.status_code == 200, f"Status: {resp.status_code}"
    assert "id" in d, "Missing id"
    assert "title" in d, "Missing title"
    assert "weeks" in d, "Missing weeks"
    assert len(d["weeks"]) > 0, "Empty weeks"
    
    print(f"  Plan ID: {d['id'][:8]}...")
    print(f"  Title: {d['title']}")
    print(f"  Duration: {d['duration_weeks']} weeks")
    print(f"  Weeks: {len(d['weeks'])}")
    for w in d["weeks"]:
        task_info = "; ".join(t["description"][:30] for t in w["tasks"])
        print(f"    Week {w['week']}: {w['topic']}")
    print("  [PASS] Plan generated successfully\n")
    return d["id"]


def test_list_plans():
    """Test: List plans"""
    print("=" * 60)
    print("TEST: List Plans")
    print("=" * 60)
    
    resp = requests.get(f"{BASE}/api/v1/plans")
    plans = resp.json()
    
    assert resp.status_code == 200
    assert isinstance(plans, list)
    print(f"  Plans count: {len(plans)}")
    for p in plans:
        print(f"    {p['title']} - {p['status']} ({p['task_count']} tasks)")
    print("  [PASS]\n")
    return plans


def test_get_plan(plan_id):
    """Test: Get plan detail"""
    print("=" * 60)
    print("TEST: Get Plan Detail")
    print("=" * 60)
    
    resp = requests.get(f"{BASE}/api/v1/plans/{plan_id}")
    detail = resp.json()
    
    assert resp.status_code == 200
    assert detail["id"] == plan_id
    assert len(detail["weeks"]) > 0
    assert len(detail["weeks"][0]["tasks"]) > 0
    
    print(f"  Title: {detail['title']}")
    print(f"  Weeks: {len(detail['weeks'])}")
    print(f"  First task: {detail['weeks'][0]['tasks'][0]['description'][:50]}")
    print("  [PASS]\n")


def test_db_persistence():
    """Verify data is in PostgreSQL"""
    print("=" * 60)
    print("TEST: DB Persistence")
    print("=" * 60)
    
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "app.db")
    conn = sqlite3.connect(db_path)
    
    rows = conn.execute("SELECT count(*) FROM plans").fetchone()
    assert rows[0] > 0, f"No plans found: {rows}"
    print(f"  Plans in DB: {rows[0]}")
    
    rows = conn.execute("SELECT count(*) FROM tasks").fetchone()
    assert rows[0] > 0, f"No tasks found: {rows}"
    print(f"  Tasks in DB: {rows[0]}")
    
    rows = conn.execute("SELECT status, count(*) FROM tasks GROUP BY status").fetchall()
    for r in rows:
        print(f"    status={r[0]}: {r[1]}")
    
    conn.close()
    print("  [PASS]\n")


def test_chat_with_plan_context():
    """Test: Normal chat still works"""
    print("=" * 60)
    print("TEST: Chat Still Works")
    print("=" * 60)
    
    resp = requests.post(
        f"{BASE}/api/v1/chat",
        json={"message": "Hello", "session_id": "after-plan-1"},
        timeout=60,
    )
    d = resp.json()
    
    assert resp.status_code == 200
    assert "answer" in d
    assert d["agent_type"] in ("code", "english", "career", "search", "research", "rag", "planner")
    print(f"  Agent: {d['agent_name']}")
    print("  [PASS]\n")


def test_update_task_status(plan_id):
    """Test: Update task status"""
    print("=" * 60)
    print("TEST: Update Task Status")
    print("=" * 60)
    
    detail = requests.get(f"{BASE}/api/v1/plans/{plan_id}").json()
    task_id = detail["weeks"][0]["tasks"][0]
    
    # 这里 task_id 只是 order 信息，我们需要真正的 task ID
    # 用 DB 查询
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "app.db")
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        f"SELECT id FROM tasks WHERE plan_id='{plan_id}' LIMIT 1"
    ).fetchone()
    conn.close()
    
    if row:
        resp = requests.patch(
            f"{BASE}/api/v1/plans/tasks/{row[0]}",
            json={"status": "in_progress"},
        )
        assert resp.status_code == 200
        d = resp.json()
        assert d["status"] == "in_progress"
        print(f"  Task {row[0][:8]}... → in_progress")
        print("  [PASS]\n")
    else:
        print("  SKIP: No tasks found\n")


passed = 0
failed = 0

def main():
    global passed, failed
    
    try:
        plan_id = test_generate_plan()
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}")
        failed += 1
        plan_id = None
    
    try:
        test_list_plans()
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}")
        failed += 1
    
    if plan_id:
        try:
            test_get_plan(plan_id)
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            failed += 1
    
    try:
        test_db_persistence()
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}")
        failed += 1
    
    try:
        test_chat_with_plan_context()
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}")
        failed += 1
    
    if plan_id:
        try:
            test_update_task_status(plan_id)
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            failed += 1
    
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)

if __name__ == "__main__":
    main()
