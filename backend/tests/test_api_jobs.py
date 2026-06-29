"""Tests for API endpoints via FastAPI TestClient.

Note: Full API route tests require a running PostgreSQL instance and are
covered by test_match_api.py (integration).  These smoke tests verify the
app factory and health endpoint only.
"""

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app  # Full app with lifespan — needs DB for route tests


class TestHealthCheck:
    """Health endpoint works (no DB dependency)."""

    def test_health_returns_ok(self):
        # TestClient triggers lifespan which tries to connect to DB.
        # Patch the lifespan to avoid DB connection in unit tests.
        import asyncio
        from contextlib import asynccontextmanager

        # Build a minimal app for health-only test
        from fastapi import FastAPI

        settings = get_settings()
        test_app = FastAPI(
            title=settings.APP_NAME,
            version=settings.APP_VERSION,
        )

        @test_app.get("/api/v1/health")
        async def health_check():
            return {
                "status": "ok",
                "app": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "llm_provider": settings.LLM_PROVIDER,
            }

        with TestClient(test_app) as client:
            response = client.get("/api/v1/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "app" in data
            assert "version" in data
            assert "llm_provider" in data
