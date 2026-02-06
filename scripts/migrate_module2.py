#!/usr/bin/env python3
"""Database migration for Module 2: Entity Extraction & Recursive Compaction.

Adds:
- entities table
- projects.compaction_depth column
- projects.last_compaction_at column
"""

import asyncio
import sqlite3
import sys
from pathlib import Path

# Add backend to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.db.database import DATABASE_URL


async def migrate():
    """Apply Module 2 schema changes."""
    
    # Extract database path from URL
    db_path = DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    
    print(f"🔧 Migrating database: {db_path}")
    
    # Use synchronous sqlite3 for migrations
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if entities table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='entities'
        """)
        entities_exists = cursor.fetchone() is not None
        
        if not entities_exists:
            print("  ✅ Creating entities table...")
            cursor.execute("""
                CREATE TABLE entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chunk_id VARCHAR(36) NOT NULL,
                    project_id VARCHAR(36) NOT NULL,
                    entity_type VARCHAR(20) NOT NULL,
                    value TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 1.0,
                    context_snippet TEXT,
                    created_at DATETIME NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX idx_entities_chunk_id ON entities(chunk_id)")
            cursor.execute("CREATE INDEX idx_entities_project_id ON entities(project_id)")
            cursor.execute("CREATE INDEX idx_entities_entity_type ON entities(entity_type)")
            print("  ✅ Entities table created")
        else:
            print("  ⏭️  Entities table already exists")
        
        # Check if projects has compaction_depth
        cursor.execute("PRAGMA table_info(projects)")
        columns = {row[1] for row in cursor.fetchall()}
        
        if 'compaction_depth' not in columns:
            print("  ✅ Adding compaction_depth column to projects...")
            cursor.execute("ALTER TABLE projects ADD COLUMN compaction_depth INTEGER DEFAULT 0")
            print("  ✅ Column added")
        else:
            print("  ⏭️  compaction_depth column already exists")
        
        if 'last_compaction_at' not in columns:
            print("  ✅ Adding last_compaction_at column to projects...")
            cursor.execute("ALTER TABLE projects ADD COLUMN last_compaction_at DATETIME")
            print("  ✅ Column added")
        else:
            print("  ⏭️  last_compaction_at column already exists")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
