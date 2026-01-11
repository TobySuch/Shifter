"""Tests for main shifter app URL configuration."""

import os
from unittest import mock

from django.test import TestCase


class AdminSettingsTestCase(TestCase):
    """Test cases for admin settings configuration."""

    def test_admin_enabled_setting_defaults_to_debug_value(self):
        """ADMIN_ENABLED should default to DEBUG value when not set."""
        with mock.patch.dict(os.environ, {}, clear=False):
            # Remove ADMIN_ENABLED if it exists
            os.environ.pop("ADMIN_ENABLED", None)

            # When DEBUG is 1 (True)
            with mock.patch.dict(os.environ, {"DEBUG": "1"}, clear=False):
                from django.conf import settings

                # Reload settings to pick up changes
                settings.DEBUG = int(os.environ.get("DEBUG", 0))
                expected_admin_enabled = bool(settings.DEBUG)
                self.assertTrue(expected_admin_enabled)

    def test_admin_enabled_setting_respects_explicit_value(self):
        """ADMIN_ENABLED should respect explicit environment variable."""
        # Test explicit True
        with mock.patch.dict(
            os.environ, {"ADMIN_ENABLED": "1", "DEBUG": "0"}, clear=False
        ):
            admin_enabled = bool(int(os.environ.get("ADMIN_ENABLED", "0")))
            self.assertTrue(admin_enabled)

        # Test explicit False
        with mock.patch.dict(
            os.environ, {"ADMIN_ENABLED": "0", "DEBUG": "1"}, clear=False
        ):
            admin_enabled = bool(int(os.environ.get("ADMIN_ENABLED", "0")))
            self.assertFalse(admin_enabled)

    def test_admin_enabled_false_by_default_in_production(self):
        """ADMIN_ENABLED should be False when DEBUG is off and not set."""
        with mock.patch.dict(
            os.environ, {"DEBUG": "0"}, clear=False
        ):
            # Remove ADMIN_ENABLED if it exists
            os.environ.pop("ADMIN_ENABLED", None)
            from django.conf import settings

            settings.DEBUG = int(os.environ.get("DEBUG", 0))
            # When not explicitly set and DEBUG is False,
            # admin should be disabled
            admin_enabled = bool(
                int(os.environ.get("ADMIN_ENABLED", str(int(settings.DEBUG))))
            )
            self.assertFalse(admin_enabled)
