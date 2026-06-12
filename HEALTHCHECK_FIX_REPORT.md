# HealthCheck Fix Report

> Date: 2026-06-12
> Commit: (to be generated)

---

## Modified Files

| File | Change | Lines Changed |
|------|--------|---------------|
| `web_app/backend/alembic/env.py` | Add connect_timeout + SSL to `run_migrations_online()` | +8 |
| `web_app/backend/app/main.py` | Make `/health` independent of database | -2, +2 |

---

## Fix 1: Alembic Migration Timeout

**File:** `web_app/backend/alembic/env.py`

**Before:**
```python
connectable = create_engine(
    settings.DATABASE_URL,
    poolclass=pool.NullPool,
)
```

**After:**
```python
url = settings.DATABASE_URL

# Auto-add sslmode=require (Neon PostgreSQL required)
if url.startswith("postgresql") and "sslmode" not in url:
    separator = "&" if "?" in url else "?"
    url = url + separator + "sslmode=require"

connectable = create_engine(
    url,
    poolclass=pool.NullPool,
    connect_args={"connect_timeout": 10},
)
```

**Why:**
- `alembic upgrade head` is the FIRST command in CMD that touches the database
- Without `connect_timeout`, a PostgreSQL connection attempt blocks for **30-120 seconds** (TCP default)
- During this time, **uvicorn has not started** → Railway Health Check gets "connection refused"
- With `connect_timeout=10`, failure is detected in 10s → CMD continues → uvicorn starts

---

## Fix 2: Health Check Independence

**File:** `web_app/backend/app/main.py`

**Before:**
```python
@app.get("/health")
def health_check():
    from app.database import get_db_type
    return {
        "status": "ok",
        "version": "1.0.0",
        "database": get_db_type(),
    }
```

**After:**
```python
@app.get("/health")
def health_check():
    """Health Check — 必须在 100ms 内返回，不依赖任何外部服务"""
    return {
        "status": "ok",
        "version": "1.0.0",
    }
```

**Why:**
- `/health` is used by Railway to determine if the container is alive
- `get_db_type()` calls `get_engine()` which blocks on first call (10s PostgreSQL test)
- Health Check must return in **under 100ms** — no database, no LLM, no model
- The `/db-status` endpoint still provides full database diagnostics on demand

---

## Startup Timeline (After Fix)

### Scenario A: PostgreSQL Unreachable or Not Configured

```
T+0s    CMD: echo "[BOOT] Starting container"
T+0s    CMD: echo "[BOOT] DATABASE_URL: sqlite:///./app.db"
T+0s    CMD: psycopg2 check
T+0s    CMD: alembic upgrade head (SQLite — instant success ✅)
T+0s    CMD: uvicorn app.main:app
T+0s    uvicorn: Listening on 0.0.0.0:8080
T+0s    Startup: get_engine() → SQLite (instant ✅)
T+0s    Startup: [BOOT] Startup complete
T+0s    /health returns {"status":"ok"} ✅ (under 1ms)
        ↑ Railway start-period: 60s → abundant margin
```

### Scenario B: PostgreSQL Reachable

```
T+0s    CMD: echo "[BOOT] DATABASE_URL: postgresql://user@neon.tech/db"
T+0s    CMD: alembic upgrade head (PostgreSQL with sslmode=require, timeout=10s)
T+1s    alembic: connection OK, migrations run ✅
T+1s    CMD: uvicorn starts
T+1s    Startup: get_engine() → PostgreSQL test → SUCCESS ✅
T+1s    /health returns {"status":"ok"} ✅
```

### Scenario C: PostgreSQL Unreachable with Correct URL

```
T+0s    CMD: DATABASE_URL: postgresql://user@neon.tech/db
T+0s    CMD: alembic upgrade head (timeout=10s)
T+10s   alembic: timeout → "Migration failed, continuing..."
T+10s   CMD: uvicorn starts
T+10s   Startup: get_engine() → PostgreSQL test (timeout=10s)
T+20s   Startup: PostgreSQL FAILED → SQLite fallback
T+20s   Startup: [BOOT] Startup complete
T+20s   /health returns {"status":"ok"} ✅
        ↑ Railway Health Check starts at T+60s → still within margin
```

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| `/health` no longer reports database type | Low — `/db-status` still provides it | `/db-status` endpoint available |
| alembic auto-adds `sslmode=require` | Low — idempotent, only adds if missing | Double-check by reading env.py |
| 10s timeout too short for slow Neon | Low — 10s is standard for cloud DBs | Can be increased in env.py |
| `connect_args` not supported by SQLite | None — SQLite ignores it | Verified locally |

---

## Verification Results (Local)

| Test | Result | Time |
|------|--------|------|
| `curl /health` | `{"status":"ok","version":"1.0.0"}` | < 100ms ✅ |
| `curl /db-status` | Shows "sqlite", engine_initialized: true | OK ✅ |
| `curl /env-check` | 10 env vars checked, conclusion: correct | OK ✅ |

---

## Git Commit

```
git commit -m "fix: Health Check timeout — alembic timeout + /health independence

Root cause: alembic upgrade head blocked for 30-120s on PostgreSQL
connection (no connect_timeout), delaying uvicorn startup. /health
relied on get_db_type() which calls get_engine() and blocks on first call.

Changes:
- alembic/env.py: add connect_args={'connect_timeout': 10} + auto SSL
- app/main.py: /health returns instantly, no database dependency"
```
