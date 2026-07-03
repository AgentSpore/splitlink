from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..schemas.link import LinkAnalytics, LinkCreate, LinkList, LinkResponse
from ..services import link_service

router = APIRouter()


@router.post("", response_model=LinkResponse, status_code=201)
async def create_link(link: LinkCreate):
    """Create a new link record."""
    link_id = await link_service.create_link(
        title=link.title,
        url=link.url,
        description=link.description,
    )
    result = await link_service.get_link(link_id)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to retrieve created link")
    return LinkResponse(
        id=result["id"],
        title=result["title"],
        url=result["url"],
        description=result["description"],
        created_at=result["created_at"],
        updated_at=result["updated_at"],
    )


@router.get("", response_model=LinkList)
async def list_links(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List all links with pagination and analytics."""
    result = await link_service.list_links(limit=limit, offset=offset)
    items = [
        LinkResponse(
            id=item["id"],
            title=item["title"],
            url=item["url"],
            description=item["description"],
            created_at=item["created_at"],
            updated_at=item["updated_at"],
        )
        for item in result["items"]
    ]
    return LinkList(items=items, total=result["total"])


@router.get("/{link_id}", response_model=LinkResponse)
async def get_link(link_id: int):
    """Get a specific link by ID."""
    result = await link_service.get_link(link_id)
    if not result:
        raise HTTPException(status_code=404, detail="Link not found")
    return LinkResponse(
        id=result["id"],
        title=result["title"],
        url=result["url"],
        description=result["description"],
        created_at=result["created_at"],
        updated_at=result["updated_at"],
    )


@router.delete("/{link_id}", status_code=204)
async def delete_link(link_id: int):
    """Delete a link and its analytics."""
    deleted = await link_service.delete_link(link_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Link not found")


@router.get("/{link_id}/analytics", response_model=LinkAnalytics)
async def get_link_analytics(link_id: int):
    """Get analytics for a specific link."""
    result = await link_service.get_link(link_id)
    if not result:
        raise HTTPException(status_code=404, detail="Link not found")
    analytics = result["analytics"]
    return LinkAnalytics(
        id=link_id,
        title=result["title"],
        total_clicks=analytics["total_clicks"],
        open_rate=analytics["open_rate"],
        average_settlement=analytics["average_settlement"],
    )
