"""
app/main.py
FastAPI application entry point for NutriGuard AI.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, analyze
from app.core.config import settings
from app.core.logging import configure_logging, get_logger

configure_logging(
    log_level=settings.LOG_LEVEL,
    is_production=settings.is_production,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("nutriguard.startup", version=settings.APP_VERSION)
    yield
    logger.info("nutriguard.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="NutriGuard AI",
        description="AI-powered food label fraud detection.",
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(analyze.router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower(),
    )