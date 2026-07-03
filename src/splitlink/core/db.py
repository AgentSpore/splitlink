import os

import aiosqlite

DB_PATH = os.environ.get("DB_PATH", "./splitlink.db")

async def get_db():
    """Async context manager yielding a connection."""
    async with aiosqlite.connect(DB_PATH) as db:
        yield db

async def init_db():
    """Create tables if they don't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS link_analytics (
                link_id INTEGER PRIMARY KEY,
                title TEXT,
                total_clicks INTEGER DEFAULT 0,
                settlement_count INTEGER DEFAULT 0,
                open_rate REAL DEFAULT 0.0,
                average_settlement REAL DEFAULT 0.0,
                FOREIGN KEY (link_id) REFERENCES links(id)
            )
        """)
        await db.commit()
