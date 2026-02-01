"""
Integration tests for Feed API.
"""
from fastapi.testclient import TestClient

from app.config import get_settings


class TestFeedAPI:
    def test_get_feed_personalized(self, test_client: TestClient):
        """Test happy path personalized feed."""
        response = test_client.get(
            "/v1/feed",
            params={"user_hash": "user_sporty", "limit": 5},
            headers={"X-Tenant-ID": "tenant_sports"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0
        assert data["is_personalized"] is True
        # Check cache headers
        assert "private" in response.headers["Cache-Control"]
        assert "max-age=30" in response.headers["Cache-Control"]
        assert "ETag" in response.headers

    def test_get_feed_cold_start(self, test_client: TestClient):
        """Test feed for unknown user (cold start)."""
        response = test_client.get(
            "/v1/feed",
            params={"user_hash": "user_unknown_123", "limit": 5},
            headers={"X-Tenant-ID": "tenant_sports"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0
        # Should still be marked personalized (even if just popularity)
        # unless fallback triggered
        assert data["is_personalized"] is True

    def test_get_feed_fallback_tenant_not_found(self, test_client: TestClient):
        """Test fallback when tenant config missing."""
        response = test_client.get(
            "/v1/feed",
            params={"user_hash": "user_sporty"},
            headers={"X-Tenant-ID": "tenant_unknown"},
        )

        # Should default to safe config & empty candidates -> fallback
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)
        assert data["is_personalized"] is False
        assert data["degraded"] is True

    def test_kill_switch(self, test_client: TestClient):
        """Test global kill switch via settings."""
        settings = get_settings()
        original_value = settings.KILL_SWITCH_ACTIVE
        settings.KILL_SWITCH_ACTIVE = True

        try:
            response = test_client.get(
                "/v1/feed",
                params={"user_hash": "user_sporty"},
                headers={"X-Tenant-ID": "tenant_sports"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["is_personalized"] is False
            assert data["degraded"] is False  # Kill switch is intentional, not an error

        finally:
            settings.KILL_SWITCH_ACTIVE = original_value

    def test_circuit_breaker_status(self, test_client: TestClient):
        """Test health endpoint shows circuit status."""
        response = test_client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["circuit_breaker"]["state"] == "closed"
