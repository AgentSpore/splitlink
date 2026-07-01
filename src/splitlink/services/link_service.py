from datetime import datetime
from typing import Optional

from aiosqlite import Connection

from ..core.db import get_db

async def create_link(title: str, url: str, description: Optional[str] = None) -> int:
    """Create a new link and initialize its analytics record."""
    async with get_db() as db:
        # Insert the link
        cursor = await db.execute(
            "INSERT INTO links (title, url, description) VALUES (?, ?, ?)",
            (title, url, description)
        )
        link_id = cursor.lastrowid
        await db.commit()
        
        # Initialize analytics for the new link
        await db.execute(
            """
            INSERT INTO link_analytics (link_id, title, total_clicks, open_rate, average_settlement)
            VALUES (?, ?, 0, 0.0, 0.0)
            """,
            (link_id, title)
        )
        await db.commit()
        
        return link_id

async def get_link(link_id: int):
    """Get a specific link with its analytics."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT l.id, l.title, l.url, l.description, l.created_at, l.updated_at,
                   a.total_clicks, a.open_rate, a.average_settlement
            FROM links l
            LEFT JOIN link_analytics a ON l.id = a.link_id
            WHERE l.id = ?
            """,
            (link_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            return None
        
        return {
            "id": row[0],
            "title": row[1],
            "url": row[2],
            "description": row[3],
            "created_at": datetime.fromisoformat(row[4]),
            "updated_at": datetime.fromisoformat(row[5]),
            "analytics": {
                "total_clicks": row[6] or 0,
                "open_rate": row[7] or 0.0,
                "average_settlement": row[8] or 0.0
            }
        }

async def list_links(limit: int = 10, offset: int = 0):
    """List all links with pagination and analytics."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM links"
        )
        total = (await cursor.fetchone())[0]
        
        cursor = await db.execute(
            """
            SELECT l.id, l.title, l.url, l.description, l.created_at, l.updated_at,
                   a.total_clicks, a.open_rate, a.average_settlement
            FROM links l
            LEFT JOIN link_analytics a ON l.id = a.link_id
            ORDER BY l.created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        )
        rows = await cursor.fetchall()
        
        items = []
        for row in rows:
            items.append({
                "id": row[0],
                "title": row[1],
                "url": row[2],
                "description": row[3],
                "created_at": datetime.fromisoformat(row[4]),
                "updated_at": datetime.fromisoformat(row[5]),
                "analytics": {
                    "total_clicks": row[6] or 0,
                    "open_rate": row[7] or 0.0,
                    "average_settlement": row[8] or 0.0
                }
            })
        
        return {"items": items, "total": total}

async def update_link_clicks(link_id: int) -> bool:
    """Increment click count for a link."""
    async with get_db() as db:
        cursor = await db.execute(
            "UPDATE link_analytics SET total_clicks = total_clicks + 1 WHERE link_id = ?",
            (link_id,)
        )
        await db.commit()
        return cursor.rowcount > 0

async def update_link_settlement(link_id: int, amount: float) -> bool:
    """Update average settlement amount for a link."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            UPDATE link_analytics
            SET average_settlement = (
                (total_clicks * average_settlement) + ?
            ) / (total_clicks + 1),
            open_rate = open_rate + 0.1
            WHERE link_id = ?
            """,
            (amount, link_id)
        )
        await db.commit()
        return cursor.rowcount > 0