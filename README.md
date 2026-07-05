# SplitLink

SplitLink is a FastAPI-powered microservice for creating and tracking payment split links. Generate sharable links that recipients can use to contribute to pooled expenses, with built-in analytics for tracking clicks, open rates, and average settlement amounts.

## Features

- **Generate payment split links** — Create shareable URLs for pooling expenses across multiple people
- **Update existing links** — Partially update a link's title, URL, or description without recreating it
- **Real-time analytics** — Track link clicks, open rates, and average settlement amounts
- **Search and filter** — Search links by title, URL, or description
- **Demo data on first run** — Comes pre-seeded with example links so the UI is never blank
- **FastAPI layered architecture** — Clean separation of concerns with core, api, services, and schemas
- **Async SQLite database** — Zero-config persistence with aiosqlite
- **Docker support** — Containerized deployment with Python 3.11 slim
- **CORS enabled** — Ready for frontend integration

## Architecture

```
splitlink/
├── src/splitlink/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, CORS, health endpoint, global error handler
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py         # Pydantic settings
│   │   └── db.py             # aiosqlite connection & schema init, demo data seed
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── link.py           # Pydantic models (Create/Read/Update/List/Analytics)
│   ├── api/
│   │   ├── __init__.py
│   │   └── link.py           # APIRouter with CRUD + click/settlement/search endpoints
│   └── services/
│       ├── __init__.py
│       └── link_service.py   # Business logic with async aiosqlite queries
├── tests/
│   └── test_api.py           # 45+ tests covering all endpoints, search, and input validation
├── frontend/
│   └── index.html            # Buildless UI with Tailwind CSS CDN
├── Dockerfile
├── .env.example
├── pyproject.toml
└── README.md
```

## Tech Stack

- **Framework:** FastAPI 0.115+
- **Python:** 3.11+
- **Database:** SQLite with aiosqlite 0.20+
- **Data Validation:** Pydantic 2.9+ & pydantic-settings 2.5+
- **HTTP Client:** httpx 0.27+
- **Logging:** loguru 0.7+
- **Packaging:** hatchling
- **Testing:** pytest 8+ with pytest-asyncio
- **Frontend:** Vanilla JS + Tailwind CSS (CDN, no build step)

## Getting Started

### Prerequisites

- Python 3.11 or higher
- pip or poetry

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/AgentSpore/splitlink.git
cd splitlink
```

2. Install dependencies:
```bash
pip install -e .
```

3. Copy the environment template:
```bash
cp .env.example .env
```

4. Edit `.env` to configure settings if needed (default values work for development).

5. Run the application:
```bash
uvicorn splitlink.main:app --reload --host 0.0.0.0 --port 8000
```

6. The API will be available at `http://localhost:8000` with a web UI at the root URL.

### Running Tests

```bash
pip install -e ".[dev]"
pytest -v --asyncio-mode=auto
```

Tests use an in-memory SQLite database and cover all CRUD operations, search filtering, click tracking, settlement recording, analytics retrieval, and partial updates.

### API Endpoints

#### Health Check
```bash
GET /health
```
Returns API health status.

#### Links

**Create a split link**
```bash
POST /api/links
Content-Type: application/json

{
  "title": "Trip to Tokyo",
  "url": "https://example.com/pay/splitlink/abc123",
  "description": "Split $500 for flight + hotel"
}
```
Returns the created link with initial analytics (status: 201).

**Update a link (partial)**
```bash
PATCH /api/links/{link_id}
Content-Type: application/json

{
  "title": "Updated Title",
  "description": "Updated description"
}
```
All fields are optional — only the provided fields are updated. Accepts `title`, `url`, and/or `description`. Set `"description": null` to clear the description. Returns the full updated link with analytics. Returns 404 if the link does not exist.

**List all links (with optional search)**
```bash
GET /api/links?limit=10&offset=0
GET /api/links?search=Tokyo&limit=10&offset=0
```
The optional `search` parameter filters links by title, URL, or description (case-insensitive LIKE match). Response includes `items` and `total` for pagination.

**Get a specific link**
```bash
GET /api/links/{link_id}
```
Returns the link with its full analytics. Returns 404 if not found.

**Delete a link**
```bash
DELETE /api/links/{link_id}
```
Deletes the link and its analytics record. Returns 204 (no content) on success, 404 if not found.

**Record a click**
```bash
POST /api/links/{link_id}/click
```
Increments the click counter and recalculates open rate. Returns updated analytics.

**Record a settlement**
```bash
POST /api/links/{link_id}/settlement
Content-Type: application/json

{ "amount": 150.00 }
```
Records a settlement amount, increments both click and settlement counters, and updates weighted average. Amount must be > 0. Returns updated analytics.

**Get link analytics**
```bash
GET /api/links/{link_id}/analytics
```
Returns `total_clicks`, `settlement_count`, `open_rate` (0–1), and `average_settlement`.

### Docker Deployment

1. Build the Docker image:
```bash
docker build -t splitlink .
```

2. Run the container:
```bash
docker run -p 8000:8000 --env-file .env splitlink
```

3. The API will be available at `http://localhost:8000`

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_PATH` | Path to SQLite database file | `./splitlink.db` |
| `CORS_ORIGINS` | List of allowed CORS origins | `["*"]` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

## Database Schema

### Links Table
- `id` — Primary key (auto-increment)
- `title` — Link title
- `url` — Shareable URL
- `description` — Optional description
- `created_at` — Timestamp of creation
- `updated_at` — Timestamp of last update (refreshed on PATCH)

### Link Analytics Table
- `link_id` — Foreign key to links table
- `title` — Link title (for analytics)
- `total_clicks` — Total link clicks
- `settlement_count` — Number of settlements recorded
- `open_rate` — Open rate (`settlement_count / total_clicks`, capped at 1.0)
- `average_settlement` — Weighted average settlement amount

## Demo Data

On first startup with an empty database, SplitLink automatically seeds five demo links:

1. **Trip to Tokyo** — $2500 split with 12 clicks / 8 settlements ($312.50 avg)
2. **Team Dinner** — $900 split with 5 clicks / 3 settlements ($150.00 avg)
3. **Beach House Rental** — $3200 split with 3 clicks, no settlements yet
4. **Gift for Mom** — $400 birthday pool, no activity yet
5. **Co-working Space** — $1200 Q2 membership, no activity yet

This ensures the web UI is never blank on first visit.

## License

MIT License — see LICENSE file for details
