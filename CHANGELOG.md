# Changelog

All notable changes to the SplitLink project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2025-07-05

### Changed

- Refactored `link_service.py`: extracted `_fetch_link()` and `_fetch_analytics()` helpers to eliminate 7 duplicated JOIN-query + `_row_to_dict` blocks, reducing code duplication and improving maintainability

## [1.3.0] - 2025-07-05

### Added

- README: Document PATCH `/api/links/{link_id}` endpoint with request/response examples
- README: Add "Update existing links" to Features section
- README: Note `updated_at` behavior (refreshed on PATCH) in Schema section
- README: Update architecture tree to reflect `LinkUpdate` schema in schemas listing
- README: Update test count from "30+" to "45+"
- README: Add PATCH endpoint to Getting Started / Running Tests section

## [1.2.0] - 2025-07-05

### Added

- PATCH `/api/links/{link_id}` endpoint for partial updates to title, url, and/or description
- `LinkUpdate` Pydantic schema with all optional fields
- `update_link` service function that builds dynamic SQL SET clauses
- Tests for update endpoint: title-only, url-only, description-only, clear description,
  all fields, empty body, missing link, analytics preservation, timestamp update

## [1.1.0] - 2025-07-02

### Added

- CHANGELOG.md — project changelog following Keep a Changelog format
- LICENSE — MIT license file
- pytest test suite — 30+ tests covering CRUD operations, analytics, health check, search, input validation
- Comprehensive README documentation with architecture diagram, API reference, and deployment guide

### Fixed

- pyproject.toml — filled empty `description` field with project summary
- pyproject.toml — added ruff lint configuration for code quality

## [1.0.0] - 2025-07-02

### Added

- FastAPI application scaffold with layered architecture (core, api, services, schemas)
- Payment split link generation — create shareable URLs for pooling expenses
- Link analytics — track clicks, open rates, and average settlement amounts
- Async SQLite database with aiosqlite — zero-config persistence
- RESTful CRUD API for links (create, read, list, delete) with pagination
- Click and settlement tracking endpoints
- Search and filter links by title, URL, or description
- Analytics API endpoint per link
- Health check endpoint at GET /health
- CORS middleware for frontend integration
- Pydantic models for request/response validation
- Environment configuration via pydantic-settings with .env file
- Docker single-stage build with Python 3.11-slim
- Buildless frontend with Tailwind CSS CDN
- Development dependencies: pytest, pytest-asyncio, httpx
- hatchling build system with pyproject.toml
