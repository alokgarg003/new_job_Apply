# jobspy/api/app.py
"""
Main FastAPI application factory with enhanced features.
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
import time
from datetime import datetime

from jobspy.api.routes import profiles, searches, jobs, admin
from jobspy.util import create_logger
from jobspy.config import get_config

log = create_logger("API")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown."""
    log.info("Starting JobSpy API...")
    config = get_config()
    log.info(f"Environment: {config.environment}")
    log.info(f"Database configured: {bool(config.database.url)}")

    yield

    log.info("Shutting down JobSpy API...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    config = get_config()

    app = FastAPI(
        title="JobSpy API",
        description="Intelligent Job Scraping and Matching Platform",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(GZipMiddleware, minimum_size=1000)

    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        """Add processing time header to responses."""
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler for unhandled errors."""
        log.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "detail": str(exc) if config.debug else "An unexpected error occurred",
                "code": "INTERNAL_ERROR"
            }
        )

    app.include_router(profiles.router, prefix="/api/v1", tags=["Profiles"])
    app.include_router(searches.router, prefix="/api/v1", tags=["Job Searches"])
    app.include_router(jobs.router, prefix="/api/v1", tags=["Jobs"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": "JobSpy API",
            "version": "2.0.0",
            "status": "operational",
            "docs": "/api/docs"
        }

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        from jobspy.database import get_db

        try:
            db = get_db()
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {str(e)}"

        return {
            "status": "healthy",
            "version": "2.0.0",
            "database": db_status,
            "timestamp": datetime.now().isoformat()
        }

    return app
