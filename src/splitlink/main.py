import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from .core.config import get_settings
from .core.db import init_db, seed_demo_data
from .api import link

app = FastAPI(title="SplitLink", version="0.1.0")

settings = get_settings()


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handler ──────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return a clean JSON error for any unhandled exception."""
    logger.opt(exception=exc).error("Unhandled exception on {method} {path}", method=request.method, path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


@app.on_event("startup")
async def startup_event():
    """Initialize database and seed demo data on startup."""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully")

    logger.info("Seeding demo data if empty...")
    await seed_demo_data()
    logger.info("Demo data seeded")


app.include_router(link.router, prefix="/api")

# Mount frontend static files at root — must come AFTER all routers
frontend_dir = os.environ.get("FRONTEND_DIR", "frontend")
if Path(frontend_dir).is_dir():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
    logger.info(f"Frontend mounted from {frontend_dir}")
else:
    logger.warning(f"Frontend directory {frontend_dir} not found — skipping mount")


@app.get("/health")
def health():
    return {"status": "ok"}
