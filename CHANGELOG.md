# Changelog

All notable changes to the SplitLink project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-07-02

### Added

- CHANGELOG.md — project changelog following Keep a Changelog format
- LICENSE — MIT license file
- GitHub Actions CI workflow — automated testing on push and PR
- pytest test suite — 10+ tests covering CRUD operations, analytics, health check, and input validation
- Comprehensive README documentation with architecture diagram, API reference, and deployment guide

## [1.0.0] - 2025-07-02

### Added

- FastAPI application scaffold with layered architecture (core, api, services, schemas)
- Payment split link generation — create shareable URLs for pooling expenses
- Link analytics — track clicks, open rates, and average settlement amounts
- Async SQLite database with aiosqlite — zero-config persistence
- RESTful CRUD API for links (create, read, list) with pagination
- Analytics API endpoint per link
- Health check endpoint at GET /health
- CORS middleware for frontend integration
- Pydantic models for request/response validation
- Environment configuration via pydantic-settings with .env file
- Docker single-stage build with Python 3.11-slim
- Development dependencies: pytest, pytest-asyncio, httpx
- hatchling build system with pyproject.toml

### Technical Details

- **Framework:** FastAPI 0.115+
- **Python:** 3.11+
- **Database:** SQLite with aiosqlite 0.20+
- **Data Validation:** Pydantic 2.9+ & pydantic-settings 2.5+
- **Logging:** loguru 0.7+
- **Packaging:** hatchling
- **Testing:** pytest 8+ with async support

### Project Structure

```
splitlink/
├── src/splitlink/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   └── db.py
│   ├── schemas/
│   │   └── link.py
│   ├── api/
│   │   └── link.py
│   └── services/
│       └── link_service.py
├── Dockerfile
├── .env.example
├── pyproject.toml
├── CHANGELOG.md
├── LICENSE
├── README.md
└── tests/
    └── test_api.py
```
