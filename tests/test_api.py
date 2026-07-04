import pytest
from fastapi.testclient import TestClient
from splitlink.main import app
from splitlink.core.db import init_db, get_db, seed_demo_data

import aiosqlite

TEST_DB = ":memory:"

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
async def setup_test_db():
    """Create in-memory tables using app's init_db() and override get_db for each test."""
    db = await aiosqlite.connect(TEST_DB)
    await init_db()

    async def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.clear()
    await db.close()


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_seed_demo_data():
    """Verify seed_demo_data inserts demo links when table is empty."""
    async with aiosqlite.connect(TEST_DB) as db:
        async def _override():
            yield db
        app.dependency_overrides[get_db] = _override

        await init_db()
        await seed_demo_data()

        cursor = await db.execute("SELECT COUNT(*) FROM links")
        count = (await cursor.fetchone())[0]
        assert count == 5, f"Expected 5 demo links, got {count}"

        cursor = await db.execute("SELECT title FROM links ORDER BY created_at ASC")
        rows = await cursor.fetchall()
        titles = [r[0] for r in rows]
        assert "Trip to Tokyo" in titles
        assert "Team Dinner" in titles
        assert "Beach House Rental" in titles

        # Verify idempotent — second call adds nothing
        await seed_demo_data()
        cursor = await db.execute("SELECT COUNT(*) FROM links")
        assert (await cursor.fetchone())[0] == 5

        # Verify first link has analytics
        cursor = await db.execute(
            "SELECT total_clicks, settlement_count FROM link_analytics WHERE link_id = 1"
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] == 12  # Trip to Tokyo has 12 clicks

        app.dependency_overrides.clear()


class TestCreateLink:
    def test_create_valid(self):
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
        assert resp.json()["title"] == "Test"

    def test_get_missing(self):
        resp = client.get("/api/links/99999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


class TestListLinks:
    def test_list_paginated(self):
        for i in range(5):
            client.post(
                "/api/links",
                json={"title": f"Link {i}", "url": f"https://example.com/{i}"},
            )
        resp = client.get("/api/links?limit=2&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    def test_list_empty(self):
        resp = client.get("/api/links")
        assert resp.status_code == 200
        assert resp.json() == {"items": [], "total": 0}

    def test_list_default_limit(self):
        for i in range(20):
            client.post(
                "/api/links",
                json={"title": f"Link {i}", "url": f"https://example.com/{i}"},
            )
        resp = client.get("/api/links")
        assert len(resp.json()["items"]) == 10
        assert resp.json()["total"] == 20

    def test_list_search_by_title(self):
        client.post(
            "/api/links",
            json={"title": "Tokyo Trip", "url": "https://example.com/tokyo"},
        )
        client.post(
            "/api/links",
            json={"title": "Paris Trip", "url": "https://example.com/paris"},
        )
        resp = client.get("/api/links?search=Tokyo")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Tokyo Trip"

    def test_list_search_by_url(self):
        client.post(
            "/api/links",
            json={"title": "A", "url": "https://example.com/unique-find-me"},
        )
        client.post(
            "/api/links",
            json={"title": "B", "url": "https://example.com/other"},
        )
        resp = client.get("/api/links?search=unique-find-me")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_search_by_description(self):
        client.post(
            "/api/links",
            json={
                "title": "Trip",
                "url": "https://example.com/t",
                "description": "Split $500 for flights",
            },
        )
        client.post(
            "/api/links",
            json={
                "title": "Other",
                "url": "https://example.com/o",
                "description": "Hotel booking",
            },
        )
        resp = client.get("/api/links?search=flights")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_search_no_results(self):
        client.post(
            "/api/links",
            json={"title": "Test", "url": "https://example.com/test"},
        )
        resp = client.get("/api/links?search=zzzznonexistent")
        assert resp.status_code == 200
        assert resp.json() == {"items": [], "total": 0}

    def test_list_search_case_insensitive(self):
        client.post(
            "/api/links",
            json={"title": "SPECIAL EVENT", "url": "https://example.com/special"},
        )
        resp = client.get("/api/links?search=special")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_search_with_pagination(self):
        for i in range(5):
            client.post(
                "/api/links",
                json={
                    "title": f"Matching {i}",
                    "url": f"https://example.com/m{i}",
                },
            )
        client.post(
            "/api/links",
            json={"title": "Other", "url": "https://example.com/other"},
        )
        resp = client.get("/api/links?search=Matching&limit=2&offset=0")
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        # Verify items have analytics in response
        assert "analytics" in data["items"][0]
        assert "total_clicks" in data["items"][0]["analytics"]

    def test_list_items_have_analytics(self):
        """Verify list endpoint returns analytics embedded in each item."""
        client.post(
            "/api/links",
            json={"title": "Analytics Check", "url": "https://example.com/ac"},
        )
        resp = client.get("/api/links")
        item = resp.json()["items"][0]
        assert "analytics" in item
        assert "total_clicks" in item["analytics"]
        assert "open_rate" in item["analytics"]
        assert "average_settlement" in item["analytics"]


class TestDeleteLink:
    def test_delete_existing(self):
        create = client.post(
            "/api/links", json={"title": "Del", "url": "https://example.com/del"}
        )
        lid = create.json()["id"]
        resp = client.delete(f"/api/links/{lid}")
        assert resp.status_code == 204
        resp = client.get(f"/api/links/{lid}")
        assert resp.status_code == 404

    def test_delete_missing(self):
        resp = client.delete("/api/links/99999")
        assert resp.status_code == 404


class TestClick:
    def test_record_click_increments(self):
        create = client.post(
            "/api/links",
            json={"title": "Click Test", "url": "https://example.com/click"},
        )
        lid = create.json()["id"]
        resp = client.post(f"/api/links/{lid}/click")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_clicks"] == 1

    def test_record_click_multiple(self):
        create = client.post(
            "/api/links",
            json={"title": "Multi Click", "url": "https://example.com/mclick"},
        )
        lid = create.json()["id"]
        for _ in range(5):
            client.post(f"/api/links/{lid}/click")
        resp = client.get(f"/api/links/{lid}/analytics")
        assert resp.json()["total_clicks"] == 5

    def test_record_click_nonexistent(self):
        resp = client.post("/api/links/99999/click")
        assert resp.status_code == 404


class TestSettlement:
    def test_record_settlement(self):
        create = client.post(
            "/api/links",
            json={"title": "Settlement Test", "url": "https://example.com/settle"},
        )
        lid = create.json()["id"]
        resp = client.post(
            f"/api/links/{lid}/settlement", json={"amount": 100.0}
        )
        assert resp.status_code == 200
        data = resp.json()
        # 1 settlement, 1 click total → open_rate = 1/1 = 1.0
        assert data["average_settlement"] == 100.0
        assert data["open_rate"] == 1.0

    def test_record_settlement_multiple(self):
        create = client.post(
            "/api/links",
            json={"title": "Multi Settle", "url": "https://example.com/msettle"},
        )
        lid = create.json()["id"]
        # 1st settlement: avg = 50, clicks=1, settlements=1
        client.post(f"/api/links/{lid}/settlement", json={"amount": 50.0})
        # 2nd: avg = (50 + 150)/2 = 100, clicks=2, settlements=2
        client.post(f"/api/links/{lid}/settlement", json={"amount": 150.0})
        resp = client.get(f"/api/links/{lid}/analytics")
        data = resp.json()
        assert data["average_settlement"] == 100.0
        assert data["total_clicks"] == 2
        assert data["open_rate"] == 1.0  # 2/2 = 1.0

    def test_record_settlement_negative_amount(self):
        create = client.post(
            "/api/links",
            json={"title": "Neg", "url": "https://example.com/neg"},
        )
        lid = create.json()["id"]
        resp = client.post(
            f"/api/links/{lid}/settlement", json={"amount": -10}
        )
        assert resp.status_code == 422

    def test_record_settlement_nonexistent(self):
        resp = client.post(
            "/api/links/99999/settlement", json={"amount": 50.0}
        )
        assert resp.status_code == 404

    def test_mixed_clicks_and_settlements(self):
        """Clicks + settlements: open_rate = settlements / total_clicks."""
        create = client.post(
            "/api/links",
            json={"title": "Mixed", "url": "https://example.com/mixed"},
        )
        lid = create.json()["id"]
        # 2 clicks (no settlements)
        client.post(f"/api/links/{lid}/click")
        client.post(f"/api/links/{lid}/click")
        data = client.get(f"/api/links/{lid}/analytics").json()
        assert data["total_clicks"] == 2
        assert data["open_rate"] == 0.0
        # 1 settlement (also increments clicks)
        client.post(f"/api/links/{lid}/settlement", json={"amount": 75.0})
        data = client.get(f"/api/links/{lid}/analytics").json()
        assert data["total_clicks"] == 3
        assert data["open_rate"] == 1.0 / 3.0  # 1/3 ≈ 0.333
        assert round(data["open_rate"], 4) == round(1.0 / 3.0, 4)


class TestAnalytics:
    def test_analytics_initial(self):
        create = client.post(
            "/api/links",
            json={"title": "Analytics Test", "url": "https://example.com/analytics"},
        )
        lid = create.json()["id"]
        resp = client.get(f"/api/links/{lid}/analytics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_clicks"] == 0
        assert data["open_rate"] == 0.0
        assert data["average_settlement"] == 0.0

    def test_analytics_nonexistent_link(self):
        resp = client.get("/api/links/99999/analytics")
        assert resp.status_code == 404
