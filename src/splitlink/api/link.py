from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

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


def _dict_to_link_response(data: dict) -> LinkResponse:
    """Convert a service-layer dict to a LinkResponse Pydantic model."""
    return LinkResponse(
        id=data["id"],
        title=data["title"],
        url=data["url"],
        description=data.get("description"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def _dict_to_link_with_analytics(data: dict) -> LinkWithAnalyticsResponse:
    """Convert a service-layer dict (including analytics) to a LinkWithAnalyticsResponse."""
    analytics = data.get("analytics", {})
    return LinkWithAnalyticsResponse(
        id=data["id"],
        title=data["title"],
        url=data["url"],
        description=data.get("description"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        analytics=AnalyticsData(
            total_clicks=analytics.get("total_clicks", 0),
            settlement_count=analytics.get("settlement_count", 0),
            open_rate=analytics.get("open_rate", 0.0),
            average_settlement=analytics.get("average_settlement", 0.0),
        ),
    )


def _dict_to_link_analytics(data: dict) -> LinkAnalytics:
    """Convert a service-layer dict to a LinkAnalytics model for the /analytics endpoint."""
    analytics = data.get("analytics", {})
    return LinkAnalytics(
        id=data["id"],
        title=data["title"],
        total_clicks=analytics.get("total_clicks", 0),
        settlement_count=analytics.get("settlement_count", 0),
        open_rate=analytics.get("open_rate", 0.0),
        average_settlement=analytics.get("average_settlement", 0.0),
    )


@router.post("", response_model=LinkWithAnalyticsResponse, status_code=201)
async def create_link(body: LinkCreate):
    """Create a new link.

    Returns the created link with its initial analytics (all zeros).
    """
    link = await link_service.create_link(
        title=body.title,
        url=str(body.url),
        description=body.description,
    )
    return _dict_to_link_with_analytics(link)


@router.get("", response_model=LinkList)
async def list_links(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
):
    """List links with pagination and optional search.

    Returns ``{items: [...], total: N}`` where items have embedded analytics.
    """
    result = await link_service.list_links(limit=limit, offset=offset, search=search)
    return LinkList(
        items=[_dict_to_link_with_analytics(item) for item in result["items"]],
        total=result["total"],
    )


@router.get("/{link_id}", response_model=LinkWithAnalyticsResponse)
async def get_link(link_id: int):
    """Get a single link with its full analytics.

    Raises 404 if the link does not exist.
    """
    link = await link_service.get_link(link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    return _dict_to_link_with_analytics(link)


@router.delete("/{link_id}", status_code=204)
async def delete_link(link_id: int):
    """Delete a link and its analytics record.

    Returns 204 on success, 404 if the link was not found.
    """
    deleted = await link_service.delete_link(link_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Link not found")


@router.post("/{link_id}/click", response_model=AnalyticsData)
async def record_click(link_id: int):
    """Increment the click counter for a link.

    Returns the updated analytics (total_clicks, open_rate, etc.).
    Raises 404 if the link does not exist.
    """
    result = await link_service.update_link_clicks(link_id)
    if not result:
        raise HTTPException(status_code=404, detail="Link not found")
    a = result["analytics"]
    return AnalyticsData(
        total_clicks=a.get("total_clicks", 0),
        settlement_count=a.get("settlement_count", 0),
        open_rate=a.get("open_rate", 0.0),
        average_settlement=a.get("average_settlement", 0.0),
    )


@router.post("/{link_id}/settlement", response_model=AnalyticsData)
async def record_settlement(link_id: int, body: SettlementCreate):
    """Record a settlement for a link.

    Accepts ``{\"amount\": N}`` where N > 0. The amount increments both
    total_clicks and settlement_count, recalculating open_rate and
    average_settlement.

    Returns the updated analytics dict.
    Raises 404 if the link does not exist, 422 if amount is invalid.
    """
    result = await link_service.update_link_settlement(link_id, body.amount)
    if not result:
        raise HTTPException(status_code=404, detail="Link not found")
    a = result["analytics"]
    return AnalyticsData(
        total_clicks=a.get("total_clicks", 0),
        settlement_count=a.get("settlement_count", 0),
        open_rate=a.get("open_rate", 0.0),
        average_settlement=a.get("average_settlement", 0.0),
    )


@router.get("/{link_id}/analytics", response_model=LinkAnalytics)
async def get_link_analytics(link_id: int):
    """Get analytics summary for a link.

    Returns total_clicks, settlement_count, open_rate, average_settlement.
    Raises 404 if the link does not exist.
    """
    link = await link_service.get_link(link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    return _dict_to_link_analytics(link)
