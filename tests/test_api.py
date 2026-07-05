import pytest
from fastapi.testclient import TestClient

from splitlink.main import app

client = TestClient(app)


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
async def setup_test_db():
    """Ensure a clean in-memory database before each test."""
    import os
    # Set env BEFORE importing db module so Settings picks it up
    os.environ["DB_PATH"] = ":memory:"
    # Force re-import to pick up the new env var
    import importlib
    import splitlink.core.config as cfg_mod
    import splitlink.core.db as db_mod
    importlib.reload(cfg_mod)
    importlib.reload(db_mod)
    from splitlink.core.db import init_db
    await init_db()
    # Do NOT seed demo data for tests — each test controls its own state


class TestHealth:
    def test_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestCreateLink:
    def test_create_basic(self):
        resp = client.post(
            "/api/links",
            json={"title": "Trip to Tokyo", "url": "https://example.com/pay/abc"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Trip to Tokyo"
        assert data["id"] > 0

    def test_create_with_description(self):
        resp = client.post(
            "/api/links",
            json={
                "title": "Hotel",
                "url": "https://example.com/pay/def",
                "description": "Split $500 for flight + hotel",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["description"] == "Split $500 for flight + hotel"

    def test_create_missing_title(self):
        resp = client.post("/api/links", json={"url": "https://example.com"})
        assert resp.status_code == 422

    def test_create_duplicate_url(self):
        client.post(
            "/api/links",
            json={"title": "A", "url": "https://example.com/dup"},
        )
        resp = client.post(
            "/api/links",
            json={"title": "B", "url": "https://example.com/dup"},
        )
        assert resp.status_code == 201


class TestGetLink:
    def test_get_existing(self):
        create = client.post(
            "/api/links", json={"title": "Test", "url": "https://example.com/t"}
        )
        lid = create.json()["id"]
        resp = client.get(f"/api/links/{lid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Test"
        # Verify analytics are returned inline
        assert "analytics" in data
        assert "settlement_count" in data["analytics"]
        assert data["analytics"]["total_clicks"] == 0
        assert data["analytics"]["open_rate"] == 0.0
        assert data["analytics"]["average_settlement"] == 0.0

    def test_get_missing(self):
        resp = client.get("/api/links/99999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


class TestListLinks:
    def test_list_paginated(self):
        for i in range(5):
            client.post(
                "/api/links",
                json={
                    "title": f"Link {i}",
                    "url": f"https://example.com/{i}",
                },
            )
        resp = client.get("/api/links?limit=2&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    def test_list_search(self):
        client.post(
            "/api/links",
            json={"title": "Tokyo Trip", "url": "https://example.com/tokyo"},
        )
        client.post(
            "/api/links",
            json={"title": "Paris Hotel", "url": "https://example.com/paris"},
        )
        resp = client.get("/api/links?search=tokyo")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Tokyo Trip"

    def test_list_search_url(self):
        client.post(
            "/api/links",
            json={"title": "A", "url": "https://example.com/uniquekey"},
        )
        resp = client.get("/api/links?search=uniquekey")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_search_description(self):
        client.post(
            "/api/links",
            json={
                "title": "A",
                "url": "https://example.com/a",
                "description": "unique description keyword",
            },
        )
        resp = client.get("/api/links?search=unique+description")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_search_no_match(self):
        resp = client.get("/api/links?search=zzzzz_nonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []


class TestDeleteLink:
    def test_delete_existing(self):
        create = client.post(
            "/api/links", json={"title": "Del", "url": "https://example.com/del"}
        )
        lid = create.json()["id"]
        resp = client.delete(f"/api/links/{lid}")
        assert resp.status_code == 204
        # Verify it's gone
        resp = client.get(f"/api/links/{lid}")
        assert resp.status_code == 404

    def test_delete_missing(self):
        resp = client.delete("/api/links/99999")
        assert resp.status_code == 404


class TestClick:
    def test_record_click(self):
        create = client.post(
            "/api/links", json={"title": "C", "url": "https://example.com/c"}
        )
        lid = create.json()["id"]
        resp = client.post(f"/api/links/{lid}/click")
        assert resp.status_code == 200
        assert resp.json()["total_clicks"] == 1

    def test_click_multiple(self):
        create = client.post(
            "/api/links", json={"title": "M", "url": "https://example.com/m"}
        )
        lid = create.json()["id"]
        for _ in range(5):
            client.post(f"/api/links/{lid}/click")
        resp = client.post(f"/api/links/{lid}/click")
        assert resp.status_code == 200
        assert resp.json()["total_clicks"] == 6

    def test_click_missing_link(self):
        resp = client.post("/api/links/99999/click")
        assert resp.status_code == 404


class TestSettlement:
    def test_record_settlement(self):
        create = client.post(
            "/api/links", json={"title": "S", "url": "https://example.com/s"}
        )
        lid = create.json()["id"]
        resp = client.post(
            f"/api/links/{lid}/settlement", json={"amount": 100.0}
        )
        assert resp.status_code == 200
        assert resp.json()["settlement_count"] == 1
        assert resp.json()["average_settlement"] == 100.0

    def test_settlement_weighted_avg(self):
        create = client.post(
            "/api/links", json={"title": "W", "url": "https://example.com/w"}
        )
        lid = create.json()["id"]
        client.post(f"/api/links/{lid}/settlement", json={"amount": 50.0})
        client.post(f"/api/links/{lid}/settlement", json={"amount": 100.0})
        client.post(f"/api/links/{lid}/settlement", json={"amount": 150.0})
        resp = client.post(f"/api/links/{lid}/settlement", json={"amount": 100.0})
        assert resp.status_code == 200
        assert resp.json()["settlement_count"] == 4
        # (50 + 100 + 150 + 100) / 4 = 100.0
        assert resp.json()["average_settlement"] == 100.0

    def test_settlement_updates_click_rate(self):
        create = client.post(
            "/api/links", json={"title": "R", "url": "https://example.com/r"}
        )
        lid = create.json()["id"]
        # 2 clicks, 1 settlement → open_rate = 0.5
        client.post(f"/api/links/{lid}/click")
        client.post(f"/api/links/{lid}/click")
        resp = client.post(f"/api/links/{lid}/settlement", json={"amount": 75.0})
        assert resp.status_code == 200
        assert resp.json()["total_clicks"] == 3
        assert resp.json()["settlement_count"] == 1
        assert resp.json()["open_rate"] == pytest.approx(1.0 / 3.0)
        assert resp.json()["average_settlement"] == 75.0

    def test_settlement_missing_link(self):
        resp = client.post("/api/links/99999/settlement", json={"amount": 10.0})
        assert resp.status_code == 404

    def test_settlement_zero_amount(self):
        create = client.post(
            "/api/links", json={"title": "Z", "url": "https://example.com/z"}
        )
        lid = create.json()["id"]
        resp = client.post(
            f"/api/links/{lid}/settlement", json={"amount": 0}
        )
        assert resp.status_code == 422

    def test_settlement_negative_amount(self):
        create = client.post(
            "/api/links", json={"title": "N", "url": "https://example.com/n"}
        )
        lid = create.json()["id"]
        resp = client.post(
            f"/api/links/{lid}/settlement", json={"amount": -50.0}
        )
        assert resp.status_code == 422


class TestAnalytics:
    def test_analytics_endpoint(self):
        create = client.post(
            "/api/links", json={"title": "A", "url": "https://example.com/a"}
        )
        lid = create.json()["id"]
        client.post(f"/api/links/{lid}/click")
        client.post(f"/api/links/{lid}/settlement", json={"amount": 50.0})
        resp = client.get(f"/api/links/{lid}/analytics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_clicks"] == 2
        assert data["settlement_count"] == 1
        assert data["average_settlement"] == 50.0

    def test_analytics_missing(self):
        resp = client.get("/api/links/99999/analytics")
        assert resp.status_code == 404


class TestUpdateLink:
    """Tests for PATCH /api/links/{link_id} — partial update of link fields."""

    def test_update_title(self):
        create = client.post(
            "/api/links",
            json={"title": "Old Title", "url": "https://example.com/u1"},
        )
        lid = create.json()["id"]
        resp = client.patch(
            f"/api/links/{lid}",
            json={"title": "Updated Title"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Updated Title"
        assert data["url"] == "https://example.com/u1"  # unchanged

    def test_update_url(self):
        create = client.post(
            "/api/links",
            json={"title": "URL Test", "url": "https://example.com/old"},
        )
        lid = create.json()["id"]
        resp = client.patch(
            f"/api/links/{lid}",
            json={"url": "https://example.com/new"},
        )
        assert resp.status_code == 200
        assert resp.json()["url"] == "https://example.com/new"

    def test_update_description(self):
        create = client.post(
            "/api/links",
            json={
                "title": "Desc Test",
                "url": "https://example.com/d",
                "description": "Old description",
            },
        )
        lid = create.json()["id"]
        resp = client.patch(
            f"/api/links/{lid}",
            json={"description": "New description"},
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "New description"

    def test_update_clear_description(self):
        create = client.post(
            "/api/links",
            json={
                "title": "Clear Desc",
                "url": "https://example.com/cd",
                "description": "Remove me",
            },
        )
        lid = create.json()["id"]
        resp = client.patch(
            f"/api/links/{lid}",
            json={"description": None},
        )
        assert resp.status_code == 200
        assert resp.json()["description"] is None

    def test_update_updates_timestamp(self):
        create = client.post(
            "/api/links",
            json={"title": "Time Test", "url": "https://example.com/ts"},
        )
        lid = create.json()["id"]
        import time
        time.sleep(0.01)  # ensure at least 10ms passes
        resp = client.patch(
            f"/api/links/{lid}",
            json={"title": "New Time"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated_at"] > data["created_at"]

    def test_update_missing_link(self):
        resp = client.patch(
            "/api/links/99999",
            json={"title": "Ghost"},
        )
        assert resp.status_code == 404

    def test_update_empty_body(self):
        create = client.post(
            "/api/links",
            json={"title": "Empty", "url": "https://example.com/empty"},
        )
        lid = create.json()["id"]
        resp = client.patch(f"/api/links/{lid}", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Empty"  # unchanged

    def test_update_all_fields(self):
        create = client.post(
            "/api/links",
            json={
                "title": "All",
                "url": "https://example.com/all",
                "description": "Original",
            },
        )
        lid = create.json()["id"]
        resp = client.patch(
            f"/api/links/{lid}",
            json={
                "title": "All Updated",
                "url": "https://example.com/all-new",
                "description": "Updated description",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "All Updated"
        assert data["url"] == "https://example.com/all-new"
        assert data["description"] == "Updated description"

    def test_update_analytics_preserved(self):
        create = client.post(
            "/api/links",
            json={"title": "Analytics Preserve", "url": "https://example.com/ap"},
        )
        lid = create.json()["id"]
        # Add some analytics
        client.post(f"/api/links/{lid}/click")
        client.post(f"/api/links/{lid}/settlement", json={"amount": 50.0})
        # Update title
        resp = client.patch(
            f"/api/links/{lid}",
            json={"title": "Preserved Analytics"},
        )
        assert resp.status_code == 200
        a = resp.json()["analytics"]
        assert a["total_clicks"] == 2
        assert a["settlement_count"] == 1
        assert a["average_settlement"] == 50.0
