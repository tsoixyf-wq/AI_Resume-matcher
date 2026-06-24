"""FastAPI dependency injection."""

from app.core.config import get_settings


async def get_settings_dep():
    """Dependency that provides application settings."""
    return get_settings()
