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


async def seed_demo_data():
    """Insert demo links with analytics if the links table is empty.

    Idempotent — only seeds when no links exist.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM links")
        count = (await cursor.fetchone())[0]
        if count > 0:
            return

        demo_links = [
            ("Trip to Tokyo", "https://share.example.com/tokyo-2024", "Split $2500 for flight + 4 nights Shinjuku"),
            ("Team Dinner", "https://share.example.com/team-dinner-dec", "End-of-year dinner at Saison — $900 between 6 people"),
            ("Beach House Rental", "https://share.example.com/beach-house-july", "Weekend at Malibu — $3200 split 8 ways"),
            ("Gift for Mom", "https://share.example.com/mom-birthday", "Birthday gift pool — target $400"),
            ("Co-working Space", "https://share.example.com/cowork-q2", "Q2 hot desk membership — $1200 split 3 ways"),
        ]
        now = "2024-12-01 10:00:00"

        for idx, (title, url, description) in enumerate(demo_links):
            # Stagger created_at to show descending order
            cursor = await db.execute(
                "INSERT INTO links (title, url, description, created_at, updated_at) VALUES (?, ?, ?, datetime(?, ?), datetime(?, ?))",
                (title, url, description, now, f"+{idx} days", now, f"+{idx} days"),
            )
            lid = cursor.lastrowid
            # Give the first two links some realistic analytics
            if idx == 0:
                await db.execute(
                    "INSERT INTO link_analytics (link_id, title, total_clicks, settlement_count, open_rate, average_settlement) VALUES (?, ?, 12, 8, 0.667, 312.50)",
                    (lid, title),
                )
            elif idx == 1:
                await db.execute(
                    "INSERT INTO link_analytics (link_id, title, total_clicks, settlement_count, open_rate, average_settlement) VALUES (?, ?, 5, 3, 0.6, 150.00)",
                    (lid, title),
                )
            elif idx == 2:
                await db.execute(
                    "INSERT INTO link_analytics (link_id, title, total_clicks, settlement_count, open_rate, average_settlement) VALUES (?, ?, 3, 0, 0.0, 0.0)",
                    (lid, title),
                )
            else:
                await db.execute(
                    "INSERT INTO link_analytics (link_id, title, total_clicks, settlement_count, open_rate, average_settlement) VALUES (?, ?, 0, 0, 0.0, 0.0)",
                    (lid, title),
                )

        await db.commit()
