import pytest
from fastapi.testclient import TestClient
from splitlink.main import app
from splitlink.core.db import init_db, get_db

import aiosqlite

TEST_DB = ":memory:"

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
async def setup_test_db():
    """Create in-memory tables and override get_db for each test."""
    db = await aiosqlite.connect(TEST_DB)
    await db.execute(
        """CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )"""
    )
    await db.execute(
        """CREATE TABLE IF NOT EXISTS link_analytics (
            link_id INTEGER PRIMARY KEY,
            title TEXT,
            total_clicks INTEGER DEFAULT 0,
            settlement_count INTEGER DEFAULT 0,
            open_rate REAL DEFAULT 0.0,
            average_settlement REAL DEFAULT 0.0,
            FOREIGN KEY (link_id) REFERENCES links(id)
        )"""
    )
    await db.commit()

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
        assert data["settlement_count"] == 0
        assert data["open_rate"] == 0.0
        # 1 settlement (also increments clicks)
        client.post(f"/api/links/{lid}/settlement", json={"amount": 75.0})
        data = client.get(f"/api/links/{lid}/analytics").json()
        assert data["total_clicks"] == 3
        assert data["settlement_count"] == 1
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
