from datetime import datetime
from typing import Any, Optional

from ..core.db import get_db


def _row_to_dict(row: tuple) -> dict[str, Any]:
    """Convert a links+analytics JOIN row to a dictionary.

    Expects a row from the standard JOIN query (10 columns):
      l.id, l.title, l.url, l.description, l.created_at, l.updated_at,
      a.total_clicks, a.settlement_count, a.open_rate, a.average_settlement
    """
    return {
        "id": row[0],
        "title": row[1],
        "url": row[2],
        "description": row[3],
        "created_at": datetime.fromisoformat(row[4]),
        "updated_at": datetime.fromisoformat(row[5]),
        "analytics": {
            "total_clicks": row[6] or 0,
            "settlement_count": row[7] or 0,
            "open_rate": row[8] or 0.0,
            "average_settlement": row[9] or 0.0,
        },
    }


_JOIN_QUERY = """SELECT l.id, l.title, l.url, l.description, l.created_at, l.updated_at,
                        a.total_clicks, a.settlement_count, a.open_rate, a.average_settlement
                 FROM links l
                 LEFT JOIN link_analytics a ON l.id = a.link_id"""


def _recalc_open_rate(total_clicks: int, settlement_count: int) -> float:
    """Compute open_rate as settlement_count / total_clicks, capped at 1.0."""
    if total_clicks <= 0:
        return 0.0
    return min(settlement_count / total_clicks, 1.0)


async def create_link(title: str, url: str, description: Optional[str] = None) -> dict[str, Any]:
    """Create a new link and initialize its analytics record.

    Returns the full link dict (including analytics) from a single connection.
    """
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO links (title, url, description) VALUES (?, ?, ?)",
            (title, url, description),
        )
        link_id = cursor.lastrowid

        await db.execute(
            """INSERT INTO link_analytics (link_id, title, total_clicks, settlement_count, open_rate, average_settlement)
               VALUES (?, ?, 0, 0, 0.0, 0.0)""",
            (link_id, title),
        )
        await db.commit()

        # Fetch the freshly created link within the same connection
        cursor = await db.execute(
            f"{_JOIN_QUERY} WHERE l.id = ?",
            (link_id,),
        )
        row = await cursor.fetchone()
        return _row_to_dict(row) if row else {}


async def get_link(link_id: int) -> Optional[dict[str, Any]]:
    """Get a specific link with its analytics.

    Returns None if the link does not exist.
    """
    async with get_db() as db:
        cursor = await db.execute(
            f"{_JOIN_QUERY} WHERE l.id = ?",
            (link_id,),
        )
        row = await cursor.fetchone()
        return _row_to_dict(row) if row else None


async def list_links(limit: int = 10, offset: int = 0, search: Optional[str] = None) -> dict[str, Any]:
    """List all links with pagination, analytics, and optional search.

    When ``search`` is provided, filters by title / url / description (LIKE match).
    """
    async with get_db() as db:
        if search:
            pattern = f"%{search}%"
            cursor = await db.execute(
                "SELECT COUNT(*) FROM links WHERE title LIKE ? OR url LIKE ? OR description LIKE ?",
                (pattern, pattern, pattern),
            )
            total = (await cursor.fetchone())[0]

            cursor = await db.execute(
                f"""{_JOIN_QUERY}
                 WHERE l.title LIKE ? OR l.url LIKE ? OR l.description LIKE ?
                 ORDER BY l.created_at DESC LIMIT ? OFFSET ?""",
                (pattern, pattern, pattern, limit, offset),
            )
        else:
            cursor = await db.execute("SELECT COUNT(*) FROM links")
            total = (await cursor.fetchone())[0]

            cursor = await db.execute(
                f"{_JOIN_QUERY} ORDER BY l.created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
        rows = await cursor.fetchall()

        return {"items": [_row_to_dict(r) for r in rows], "total": total}


async def update_link_clicks(link_id: int) -> Optional[dict[str, Any]]:
    """Increment click count for a link and recalculate open_rate.

    Returns the full link dict (including updated analytics) if the link existed,
    or None if the link was not found.
    """
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT total_clicks, settlement_count FROM link_analytics WHERE link_id = ?",
            (link_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None

        total_clicks, settlement_count = row
        total_clicks += 1
        open_rate = _recalc_open_rate(total_clicks, settlement_count)

        await db.execute(
            "UPDATE link_analytics SET total_clicks = ?, open_rate = ? WHERE link_id = ?",
            (total_clicks, open_rate, link_id),
        )
        await db.commit()

        # Fetch the full link within the same connection
        cursor = await db.execute(
            f"{_JOIN_QUERY} WHERE l.id = ?",
            (link_id,),
        )
        return _row_to_dict(await cursor.fetchone())


async def update_link_settlement(link_id: int, amount: float) -> Optional[dict[str, Any]]:
    """Record a settlement amount for a link.

    Increments both total_clicks and settlement_count, updates
    average_settlement via weighted average, and recalculates open_rate.

    Returns the full link dict (including updated analytics) if the link existed,
    or None if the link was not found.
    """
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT total_clicks, settlement_count, average_settlement FROM link_analytics WHERE link_id = ?",
            (link_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None

        total_clicks, settlement_count, avg_settlement = row
        total_clicks += 1
        settlement_count += 1

        # Weighted average: new_avg = (old_avg * (n-1) + amount) / n
        if settlement_count == 1:
            new_avg = amount
        else:
            new_avg = (avg_settlement * (settlement_count - 1) + amount) / settlement_count

        open_rate = _recalc_open_rate(total_clicks, settlement_count)

        await db.execute(
            """UPDATE link_analytics
               SET total_clicks = ?, settlement_count = ?,
                   open_rate = ?, average_settlement = ?
               WHERE link_id = ?""",
            (total_clicks, settlement_count, open_rate, new_avg, link_id),
        )
        await db.commit()

        # Fetch the full link within the same connection
        cursor = await db.execute(
            f"{_JOIN_QUERY} WHERE l.id = ?",
            (link_id,),
        )
        return _row_to_dict(await cursor.fetchone())


async def delete_link(link_id: int) -> bool:
    """Delete a link and its analytics record.

    Returns True if a link was actually deleted.
    """
    async with get_db() as db:
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
