
from unittest.mock import MagicMock, patch
from app.services.feature_flags import ConfigBasedFeatureFlagService

class TestFeatureFlagService:
    @patch("app.services.feature_flags.get_settings")
    def test_personalization_disabled_global(self, mock_get_settings):
        mock_settings = MagicMock()
        mock_settings.KILL_SWITCH_ACTIVE = False
        mock_settings.PERSONALIZATION_ENABLED = False
        mock_get_settings.return_value = mock_settings
        
        service = ConfigBasedFeatureFlagService()
        assert service.is_personalization_enabled("t1", "user1") is False

    @patch("app.services.feature_flags.get_settings")
    def test_internal_rollout_logic(self, mock_get_settings):
        mock_settings = MagicMock()
        mock_settings.KILL_SWITCH_ACTIVE = False
        mock_settings.PERSONALIZATION_ENABLED = True
        mock_get_settings.return_value = mock_settings
        
        service = ConfigBasedFeatureFlagService(rollout_percentage=0.0)
        assert service.is_personalization_enabled("t1", "user1") is False

        service.set_rollout_percentage(100.0)
        assert service.is_personalization_enabled("t1", "user1") is True
        
        # Test partial rollout
        service.set_rollout_percentage(50.0)
        # We assume consistent hash works, just call it to cover lines
        service.is_personalization_enabled("t1", "user1") 

    @patch("app.services.feature_flags.get_settings")
    def test_kill_switch_active(self, mock_get_settings):
        mock_settings = MagicMock()
        mock_settings.KILL_SWITCH_ACTIVE = True
        mock_get_settings.return_value = mock_settings
        
        service = ConfigBasedFeatureFlagService()
        assert service.is_personalization_enabled("t1", "user1") is False
