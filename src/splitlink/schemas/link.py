from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class LinkCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    url: str = Field(..., max_length=2000)
    description: Optional[str] = Field(None, max_length=5000)

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Split payment request",
                "url": "https://example.com/splitlink/pay/abc123",
                "description": "Split $50 across 3 friends",
            }
        }


class LinkResponse(BaseModel):
    id: int
    title: str
    url: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LinkList(BaseModel):
    items: list[LinkResponse]
    total: int


class LinkAnalytics(BaseModel):
    id: int
    title: str
    total_clicks: int
    open_rate: float
    average_settlement: float


class SettlementCreate(BaseModel):
    """Request body for recording a settlement against a link."""

    amount: float = Field(..., gt=0, description="Settlement amount (must be > 0)")
