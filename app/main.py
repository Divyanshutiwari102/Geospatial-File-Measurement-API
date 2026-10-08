from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.files import router as files_router
from app.core.config import settings
from app.db.session import Base
import logging
from sqlalchemy import create_engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup using a temporary engine
    logger.info("Creating database tables...")
    # Create a temporary engine for table creation
    temp_engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False}
        if "sqlite" in settings.database_url
        else {},
    )
    Base.metadata.create_all(bind=temp_engine)
    logger.info("Database tables created.")
    # Dispose the temporary engine
    temp_engine.dispose()
    yield
    # Cleanup on shutdown (if needed)
    logger.info("Shutting down...")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Geospatial File Measurement API",
        description="API for uploading geospatial files and extracting measurements (area/length) from features.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware (adjust as needed for production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, replace with specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(files_router, prefix="/api/files", tags=["files"])

    @app.get("/")
    async def root():
        return {"message": "Geospatial File Measurement API is running"}

    return app


app = create_app()
