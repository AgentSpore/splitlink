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
        # No unique constraint — should succeed
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

        # Verify gone
        resp = client.get(f"/api/links/{lid}")
        assert resp.status_code == 404

    def test_delete_missing(self):
        resp = client.delete("/api/links/99999")
        assert resp.status_code == 404


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
