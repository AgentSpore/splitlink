from datetime import datetime
from typing import Any, Optional

from ..core.db import get_db


def _row_to_dict(row: tuple) -> dict[str, Any]:
    """Convert a links+analytics JOIN row to a dictionary."""
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
            "average_settlement": row[8] or 0.0,
        },
    }


async def create_link(title: str, url: str, description: Optional[str] = None) -> int:
    """Create a new link and initialize its analytics record.

    Returns the newly created link id.
    """
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO links (title, url, description) VALUES (?, ?, ?)",
            (title, url, description),
        )
        link_id = cursor.lastrowid

        await db.execute(
            """INSERT INTO link_analytics (link_id, title, total_clicks, open_rate, average_settlement)
               VALUES (?, ?, 0, 0.0, 0.0)""",
            (link_id, title),
        )
        await db.commit()
        return link_id


async def get_link(link_id: int) -> Optional[dict[str, Any]]:
    """Get a specific link with its analytics.

    Returns None if the link does not exist.
    """
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT l.id, l.title, l.url, l.description, l.created_at, l.updated_at,
                      a.total_clicks, a.open_rate, a.average_settlement
               FROM links l
               LEFT JOIN link_analytics a ON l.id = a.link_id
               WHERE l.id = ?""",
            (link_id,),
        )
        row = await cursor.fetchone()
        return _row_to_dict(row) if row else None


async def list_links(limit: int = 10, offset: int = 0) -> dict[str, Any]:
    """List all links with pagination and analytics."""
    async with get_db() as db:
        cursor = await db.execute("SELECT COUNT(*) FROM links")
        total = (await cursor.fetchone())[0]

        cursor = await db.execute(
            """SELECT l.id, l.title, l.url, l.description, l.created_at, l.updated_at,
                      a.total_clicks, a.open_rate, a.average_settlement
               FROM links l
               LEFT JOIN link_analytics a ON l.id = a.link_id
               ORDER BY l.created_at DESC
               LIMIT ? OFFSET ?""",
            (limit, offset),
        )
        rows = await cursor.fetchall()

        return {"items": [_row_to_dict(r) for r in rows], "total": total}


async def update_link_clicks(link_id: int) -> bool:
    """Increment click count for a link.

    Returns True if the link existed and was updated.
    """
    async with get_db() as db:
        cursor = await db.execute(
            "UPDATE link_analytics SET total_clicks = total_clicks + 1 WHERE link_id = ?",
            (link_id,),
        )
        await db.commit()
        return cursor.rowcount > 0


async def update_link_settlement(link_id: int, amount: float) -> bool:
    """Update average settlement amount for a link.

    Uses a single atomic UPDATE to avoid read-then-write races:
    new_avg = (old_avg * old_clicks + amount) / (old_clicks + 1)

    Returns True if the link existed and was updated.
    """
    async with get_db() as db:
        cursor = await db.execute(
            """UPDATE link_analytics
               SET average_settlement = (average_settlement * total_clicks + ?) / (total_clicks + 1),
                   total_clicks = total_clicks + 1,
                   open_rate = open_rate + 0.1
               WHERE link_id = ?""",
            (amount, link_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def delete_link(link_id: int) -> bool:
    """Delete a link and its analytics record.

    Returns True if a link was actually deleted.
    """
    async with get_db() as db:
        # Delete analytics first (FK-safe even without explicit FK)
        await db.execute(
            "DELETE FROM link_analytics WHERE link_id = ?",
            (link_id,),
        )
        cursor = await db.execute(
            "DELETE FROM links WHERE id = ?",
            (link_id,),
        )
        await db.commit()
        return cursor.rowcount > 0
