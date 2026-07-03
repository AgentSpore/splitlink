from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..schemas.link import (
    AnalyticsData,
    LinkAnalytics,
    LinkCreate,
    LinkList,
    LinkResponse,
    LinkWithAnalyticsResponse,
    SettlementCreate,
)
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
        LinkWithAnalyticsResponse(
            id=item["id"],
            title=item["title"],
            url=item["url"],
            description=item["description"],
            created_at=item["created_at"],
            updated_at=item["updated_at"],
            analytics=AnalyticsData(
                total_clicks=item["analytics"]["total_clicks"],
                open_rate=item["analytics"]["open_rate"],
                average_settlement=item["analytics"]["average_settlement"],
            ),
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


@router.post("/{link_id}/click", status_code=200)
async def record_click(link_id: int):
    """Record a click for a link and return the updated analytics."""
    updated = await link_service.update_link_clicks(link_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Link not found")
    result = await link_service.get_link(link_id)
    analytics = result["analytics"] if result else {}
    return LinkAnalytics(
        id=link_id,
        title=result["title"],
        total_clicks=analytics["total_clicks"],
        open_rate=analytics["open_rate"],
        average_settlement=analytics["average_settlement"],
    )


@router.post("/{link_id}/settlement", status_code=200)
async def record_settlement(link_id: int, body: SettlementCreate):
    """Record a settlement amount for a link and return updated analytics."""
    updated = await link_service.update_link_settlement(link_id, body.amount)
    if not updated:
        raise HTTPException(status_code=404, detail="Link not found")
    result = await link_service.get_link(link_id)
    analytics = result["analytics"] if result else {}
    return LinkAnalytics(
        id=link_id,
        title=result["title"],
        total_clicks=analytics["total_clicks"],
        open_rate=analytics["open_rate"],
        average_settlement=analytics["average_settlement"],
    )


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
