# SplitLink

SplitLink is a FastAPI-powered microservice for creating and tracking payment split links. Generate sharable links that recipients can use to contribute to pooled expenses, with built-in analytics for tracking clicks, open rates, and average settlement amounts.

## Features

- **Generate payment split links** - Create shareable URLs for pooling expenses across multiple people
- **Real-time analytics** - Track link clicks, open rates, and average settlement amounts
- **FastAPI layered architecture** - Clean separation of concerns with core, api, services, and schemas
- **Async SQLite database** - Zero-config persistence with aiosqlite
- **Docker support** - Containerized deployment with Python 3.11 slim
- **CORS enabled** - Ready for frontend integration

## Architecture

```
splitlink/
├── src/splitlink/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, CORS, health endpoint
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py         # Pydantic settings
│   │   └── db.py             # aiosqlite connection & schema init
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── link.py           # Pydantic models (Create/Read/List/Analytics)
│   ├── api/
│   │   ├── __init__.py
│   │   └── link.py           # APIRouter with CRUD endpoints
│   └── services/
│       ├── __init__.py
│       └── link_service.py   # Business logic with async aiosqlite
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

6. The API will be available at `http://localhost:8000`

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

**List all links**
```bash
GET /api/links?limit=10&offset=0
```

**Get a specific link**
```bash
GET /api/links/{link_id}
```

**Get link analytics**
```bash
GET /api/links/{link_id}/analytics
```

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
- `id` - Primary key (auto-increment)
- `title` - Link title
- `url` - Shareable URL
- `description` - Optional description
- `created_at` - Timestamp of creation
- `updated_at` - Timestamp of last update

### Link Analytics Table
- `link_id` - Foreign key to links table
- `title` - Link title (for analytics)
- `total_clicks` - Total link clicks
- `open_rate` - Open rate (0-1)
- `average_settlement` - Average settlement amount

## License

MIT License - see LICENSE file for details