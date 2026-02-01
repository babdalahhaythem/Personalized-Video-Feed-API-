import pytest
from fastapi.testclient import TestClient

from app.config.settings import get_settings


@pytest.mark.asyncio
async def test_cache_headers_personalized(test_client: TestClient):
    """
    Test Cache-Control and ETag for personalized content.
    """
    settings = get_settings()
    # Ensure rollout allows personalization
    original_percentage = settings.ROLLOUT_PERCENTAGE
    settings.ROLLOUT_PERCENTAGE = 100

    try:
        response = test_client.get(
            "/v1/feed",
            params={"user_hash": "user_normal", "limit": 5},
            headers={"X-Tenant-ID": "tenant_sports"}
        )
        assert response.status_code == 200

        # Verify Headers
        headers = response.headers
        assert "private" in headers["Cache-Control"]
        assert "max-age=30" in headers["Cache-Control"]
        assert "ETag" in headers
        assert "Vary" in headers
        assert "X-User-Hash" in headers["Vary"]

        etag = headers["ETag"]

        # Test Conditional Request (304)
        resp_304 = test_client.get(
            "/v1/feed",
            params={"user_hash": "user_normal", "limit": 5},
            headers={"X-Tenant-ID": "tenant_sports", "If-None-Match": etag}
        )
        assert resp_304.status_code == 304

    finally:
        get_settings.ROLLOUT_PERCENTAGE = original_percentage


@pytest.mark.asyncio
async def test_cache_headers_fallback(test_client: TestClient):
    """
    Test Cache-Control for fallback/degraded content.
    We force fallback via feature flag or rollout.
    """
    settings = get_settings()
    original_percentage = settings.ROLLOUT_PERCENTAGE
    # Force everyone to fallback
    settings.ROLLOUT_PERCENTAGE = 0

    try:
        response = test_client.get(
            "/v1/feed",
            params={"user_hash": "user_fallback", "limit": 5},
            headers={"X-Tenant-ID": "tenant_sports"}
        )
        assert response.status_code == 200
        assert response.json()["is_personalized"] is False

        # Verify Headers for Fallback
        headers = response.headers
        assert "public" in headers["Cache-Control"]
        assert "stale-while-revalidate" in headers["Cache-Control"]
        # Public cache should NOT vary by User Hash
        assert "X-User-Hash" not in headers.get("Vary", "")

    finally:
        settings.ROLLOUT_PERCENTAGE = original_percentage
