import pytest
from fastapi.testclient import TestClient

from app.config.settings import get_settings


@pytest.mark.asyncio
async def test_rollout_logic(test_client: TestClient):
    """
    Test that users are included/excluded based on rollout percentage.
    """
    settings = get_settings()
    # 1. Set Rollout to 50%
    original_percentage = settings.ROLLOUT_PERCENTAGE
    settings.ROLLOUT_PERCENTAGE = 50

    try:
        # 2. Find a user hash that should be IN (< 50)
        # Hash logic: sum(ord(c)) % 100
        user_in = "user_in"
        # Ensure it's < 50
        while (sum(ord(c) for c in user_in) % 100) >= 50:
            user_in += "a"

        # 3. Find a user hash that should be OUT (>= 50)
        user_out = "user_out"
        while (sum(ord(c) for c in user_out) % 100) < 50:
            user_out += "a"

        # 4. Request for IN user -> Personalized
        resp_in = test_client.get(
            "/v1/feed",
            params={"user_hash": user_in},
            headers={"X-Tenant-ID": "tenant_sports"}
        )
        assert resp_in.status_code == 200
        data_in = resp_in.json()
        assert data_in["is_personalized"] is True
        assert data_in.get("degraded", False) is False

        # 5. Request for OUT user -> Fallback (Not Personalized)
        resp_out = test_client.get(
            "/v1/feed",
            params={"user_hash": user_out},
            headers={"X-Tenant-ID": "tenant_sports"}
        )
        assert resp_out.status_code == 200
        data_out = resp_out.json()
        # Should be fallback
        assert data_out["is_personalized"] is False
        assert "degraded" in data_out

    finally:
        get_settings.ROLLOUT_PERCENTAGE = original_percentage
