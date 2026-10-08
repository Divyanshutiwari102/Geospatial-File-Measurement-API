from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# Cache for engine instances
_engine_cache = None
_engine_url = None


def get_engine():
    """Create and return engine based on current settings."""
    global _engine_cache, _engine_url
    url = settings.database_url
    if _engine_cache is not None and _engine_url == url:
        return _engine_cache
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False} if "sqlite" in url else {},
    )
    _engine_cache = engine
    _engine_url = url
    return engine


# Unbound sessionmaker factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False)


def get_db():
    """
    Dependency that returns a database session.
    """
    db = SessionLocal(bind=get_engine())
    try:
        yield db
    finally:
        db.close()


# Base class for declarative models
Base = declarative_base()
