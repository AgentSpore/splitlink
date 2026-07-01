from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .core.config import get_settings
from .core.db import init_db
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


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully")


app.include_router(link.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}