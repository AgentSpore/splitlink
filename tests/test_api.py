import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from splitlink.main import app
from splitlink.core.db import get_db
import aiosqlite

client = TestClient(app)

# In-memory SQLite for testing
TEST_DB = ":memory:"


@pytest.fixture(scope="function")
async def test_db():
    """Create an in-memory database for testing."""
    db = await aiosqlite.connect(TEST_DB)
    await db.execute("""
        CREATE TABLE links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    await db.execute("""
        CREATE TABLE link_analytics (
            link_id INTEGER PRIMARY KEY,
            title TEXT,
            total_clicks INTEGER DEFAULT 0,
            open_rate REAL DEFAULT 0.0,
            average_settlement REAL DEFAULT 0.0,
            FOREIGN KEY (link_id) REFERENCES links (id)
        )
    """)
    await db.commit()
    return db


@pytest.fixture(scope="function")
def override_get_db(test_db):
    """Override get_db dependency to use test database."""
    async def _get_db():
        return test_db
    app.dependency_overrides[get_db] = _get_db
    yield test_db
    app.dependency_overrides.clear()


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_create_link(override_get_db):
    """Test creating a new link."""
    response = client.post(
        "/api/links",
        json={
            "title": "Test Link",
            "url": "https://example.com/split/123",
            "description": "Test description"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Link"
    assert data["url"] == "https://example.com/split/123"
    assert data["description"] == "Test description"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_link_missing_title(override_get_db):
    """Test creating a link without required title."""
    response = client.post(
        "/api/links",
        json={
            "url": "https://example.com/split/123"
        }
    )
    assert response.status_code == 422  # Validation error


def test_get_link(override_get_db):
    """Test getting a specific link."""
    # First create a link
    create_response = client.post(
        "/api/links",
        json={
            "title": "Test Link",
            "url": "https://example.com/split/123"
        }
    )
    link_id = create_response.json()["id"]
    
    # Then get it
    response = client.get(f"/api/links/{link_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Link"
    assert data["url"] == "https://example.com/split/123"


def test_get_link_not_found(override_get_db):
    """Test getting a non-existent link."""
    response = client.get("/api/links/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_list_links(override_get_db):
    """Test listing links with pagination."""
    # Create multiple links
    for i in range(3):
        client.post(
            "/api/links",
            json={
                "title": f"Link {i}",
                "url": f"https://example.com/split/{i}"
            }
        )
    
    # List links
    response = client.get("/api/links?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) == 2
    assert data["total"] == 3


def test_list_links_default_pagination(override_get_db):
    """Test listing links with default pagination."""
    # Create multiple links
    for i in range(5):
        client.post(
            "/api/links",
            json={
                "title": f"Link {i}",
                "url": f"https://example.com/split/{i}"
            }
        )
    
    # List links with default limit
    response = client.get("/api/links")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 10  # Default limit
    assert data["total"] == 5


def test_get_link_analytics(override_get_db):
    """Test getting analytics for a link."""
    # Create a link
    create_response = client.post(
        "/api/links",
        json={
            "title": "Test Link",
            "url": "https://example.com/split/123"
        }
    )
    link_id = create_response.json()["id"]
    
    # Get analytics (should initially be zeros)
    response = client.get(f"/api/links/{link_id}/analytics")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == link_id
    assert data["title"] == "Test Link"
    assert data["total_clicks"] == 0
    assert data["open_rate"] == 0.0
    assert data["average_settlement"] == 0.0


def test_get_link_analytics_not_found(override_get_db):
    """Test getting analytics for a non-existent link."""
    response = client.get("/api/links/99999/analytics")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_list_links_empty(override_get_db):
    """Test listing links when none exist."""
    response = client.get("/api/links")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0