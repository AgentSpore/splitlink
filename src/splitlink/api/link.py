from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from aiosqlite import Connection

from ..core.db import get_db
from ..schemas.link import LinkCreate, LinkResponse, LinkList, LinkAnalytics

router = APIRouter()


@router.post("", response_model=LinkResponse, status_code=201)
async def create_link(link: LinkCreate):
    """Create a new link record."""
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO links (title, url, description) VALUES (?, ?, ?)",
            (link.title, link.url, link.description)
        )
        link_id = cursor.lastrowid
        await db.commit()
        
        cursor = await db.execute(
            "SELECT * FROM links WHERE id = ?",
            (link_id,)
        )
        row = await cursor.fetchone()
        return LinkResponse(
            id=row[0],
            title=row[1],
            url=row[2],
            description=row[3],
            created_at=datetime.fromisoformat(row[4]),
            updated_at=datetime.fromisoformat(row[5])
        )


@router.get("", response_model=LinkList)
async def list_links(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List all links with pagination."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM links"
        )
        total = (await cursor.fetchone())[0]
        
        cursor = await db.execute(
            "SELECT * FROM links ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        rows = await cursor.fetchall()
        
        items = [
            LinkResponse(
                id=row[0],
                title=row[1],
                url=row[2],
                description=row[3],
                created_at=datetime.fromisoformat(row[4]),
                updated_at=datetime.fromisoformat(row[5])
            )
            for row in rows
        ]
        
        return LinkList(items=items, total=total)


@router.get("/{link_id}", response_model=LinkResponse)
async def get_link(link_id: int):
    """Get a specific link by ID."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM links WHERE id = ?",
            (link_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Link not found")
        
        return LinkResponse(
            id=row[0],
            title=row[1],
            url=row[2],
            description=row[3],
            created_at=datetime.fromisoformat(row[4]),
            updated_at=datetime.fromisoformat(row[5])
        )


@router.get("/{link_id}/analytics", response_model=LinkAnalytics)
async def get_link_analytics(link_id: int):
    """Get analytics for a specific link."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT title, total_clicks, open_rate, average_settlement FROM link_analytics WHERE link_id = ?",
            (link_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Link not found or no analytics yet")
        
        return LinkAnalytics(
            id=link_id,
            title=row[0],
            total_clicks=row[1],
            open_rate=row[2],
            average_settlement=row[3]
        )