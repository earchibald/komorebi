"""Migration script: Add Context Oracle tables.

Creates traces, file_events, llm_usage tables and adds
trace_id column to chunks. Idempotent — safe to run multiple times.

Usage:
    python -m scripts.migrate_v1_oracle
"""

import sqlite3
import sys
from pathlib import Path


DB_PATH = Path("komorebi.db")


def _table_exists(cur: sqlite3.Cursor, name: str) -> bool:
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    )
    return cur.fetchone() is not None


def _column_exists(cur: sqlite3.Cursor, table: str, column: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def migrate(db_path: Path | None = None) -> list[str]:
    """Run all Context Oracle migrations.

    Returns list of actions taken.
    """
    path = db_path or DB_PATH
    conn = sqlite3.connect(str(path))
    cur = conn.cursor()
    actions: list[str] = []

    try:
        # 1. traces table
        if not _table_exists(cur, "traces"):
            cur.execute("""
                CREATE TABLE traces (
                    id          TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    status      TEXT NOT NULL DEFAULT 'active',
                    meta_summary TEXT,
                    created_at  DATETIME NOT NULL,
                    updated_at  DATETIME NOT NULL
                )
            """)
            cur.execute("CREATE INDEX idx_traces_status ON traces(status)")
            cur.execute("CREATE INDEX idx_traces_name ON traces(name)")
            actions.append("Created traces table")

        # 2. file_events table
        if not _table_exists(cur, "file_events"):
            cur.execute("""
                CREATE TABLE file_events (
                    id          TEXT PRIMARY KEY,
                    trace_id    TEXT NOT NULL,
                    path        TEXT NOT NULL,
                    crud_op     TEXT NOT NULL,
                    size_bytes  INTEGER,
                    hash_prefix TEXT,
                    mime_type   TEXT,
                    created_at  DATETIME NOT NULL
                )
            """)
            cur.execute(
                "CREATE INDEX idx_file_events_trace ON file_events(trace_id)"
            )
            cur.execute(
                "CREATE INDEX idx_file_events_path ON file_events(path)"
            )
            actions.append("Created file_events table")

        # 3. llm_usage table
        if not _table_exists(cur, "llm_usage"):
            cur.execute("""
                CREATE TABLE llm_usage (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name      TEXT NOT NULL,
                    input_tokens    INTEGER NOT NULL DEFAULT 0,
                    output_tokens   INTEGER NOT NULL DEFAULT 0,
                    estimated_cost  REAL NOT NULL DEFAULT 0.0,
                    request_type    TEXT,
                    created_at      DATETIME NOT NULL
                )
            """)
            cur.execute(
                "CREATE INDEX idx_llm_usage_model ON llm_usage(model_name)"
            )
            cur.execute(
                "CREATE INDEX idx_llm_usage_date ON llm_usage(created_at)"
            )
            actions.append("Created llm_usage table")

        # 4. Add trace_id to chunks
        if _table_exists(cur, "chunks") and not _column_exists(
            cur, "chunks", "trace_id"
        ):
            cur.execute("ALTER TABLE chunks ADD COLUMN trace_id TEXT")
            cur.execute(
                "CREATE INDEX idx_chunks_trace ON chunks(trace_id)"
            )
            actions.append("Added trace_id column to chunks")

        conn.commit()
    finally:
        conn.close()

    return actions


if __name__ == "__main__":
    actions = migrate()
    if actions:
        for a in actions:
            print(f"  ✅ {a}")
        print(f"\nMigration complete: {len(actions)} action(s)")
    else:
        print("No migration needed — all tables/columns already exist.")
    sys.exit(0)
