import os
import re
from io import StringIO

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from shifter_site_settings.forms import SiteSettingsForm
from shifter_site_settings.models import SiteSetting

TEST_USER_EMAIL = "iama@test.com"
TEST_USER_PASSWORD = "mytemporarypassword"


TEST_USER_EMAIL_2 = "shifter@github.com"
TEST_USER_PASSWORD_2 = "mytemporarypassword"


class SiteSettingsTestCase(TestCase):
    def setUp(self):
        out = StringIO()
        call_command(
            "createsettings",
            "--no-color",
            stdout=out,
        )

    def test_site_settings_created(self):
        max_file_size = SiteSetting.objects.get(name="max_file_size")
        self.assertEqual(
            max_file_size.value,
            settings.SITE_SETTINGS["max_file_size"]["default"],
        )

        default_expiry_offset = SiteSetting.objects.get(
            name="default_expiry_offset"
        )
        self.assertEqual(
            default_expiry_offset.value,
            str(settings.SITE_SETTINGS["default_expiry_offset"]["default"]),
        )

        max_expiry_offset = SiteSetting.objects.get(name="max_expiry_offset")
        self.assertEqual(
            max_expiry_offset.value,
            str(settings.SITE_SETTINGS["max_expiry_offset"]["default"]),
        )


class CreateSiteSettingsCommandTest(TestCase):
    def test_command_output(self):
        expected_output = ""
        for setting_key in settings.SITE_SETTINGS.keys():
            expected_output += f'Created setting "{setting_key}"\n'

        out = StringIO()
        call_command(
            "createsettings",
            "--no-color",
            stdout=out,
        )
        self.assertIn(out.getvalue(), expected_output)


class SiteSettingsViewTest(TestCase):
    def setUp(self):
        out = StringIO()
        call_command(
            "createsettings",
            "--no-color",
            stdout=out,
        )
        User = get_user_model()
        self.super_user = User.objects.create_user(
            TEST_USER_EMAIL, TEST_USER_PASSWORD, is_staff=True
        )
        self.standard_user = User.objects.create_user(
            TEST_USER_EMAIL_2, TEST_USER_PASSWORD_2
        )

    def test_site_settings_view(self):
        # Test submitting the form changes the settings values
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse("shifter_site_settings:site-settings")
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

        # Change setting values
        new_max_file_size = "10MB"
        response = client.post(
            url,
            {
                "setting_max_file_size": new_max_file_size,
                "setting_default_expiry_offset": "1",
                "setting_max_expiry_offset": "2",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            SiteSetting.get_setting("max_file_size"), new_max_file_size
        )
        self.assertEqual(SiteSetting.get_setting("default_expiry_offset"), "1")
        self.assertEqual(SiteSetting.get_setting("max_expiry_offset"), "2")

    def test_standard_user_cannot_access(self):
        # Test that a standard user cannot access the site settings page
        client = Client()
        client.login(email=TEST_USER_EMAIL_2, password=TEST_USER_PASSWORD_2)
        url = reverse("shifter_site_settings:site-settings")
        response = client.get(url)
        self.assertEqual(response.status_code, 403)

    # #427 - Setting max expiry date in hours to large number causes 500 error
    # when accessing file upload page.
    def test_max_expiry_limits(self):
        # Test submitting the form changes the settings values
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse("shifter_site_settings:site-settings")
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

        # Change setting values
        old_setting_max_expiry_offset = SiteSetting.get_setting(
            "max_expiry_offset"
        )
        setting_max_expiry_offset = "99999999999999999999999999999999999999"
        response = client.post(
            url,
            {
                "setting_max_file_size": "5120MB",
                "setting_default_expiry_offset": "336",
                "setting_max_expiry_offset": setting_max_expiry_offset,
            },
        )
        self.assertEqual(response.status_code, 200)
        # Check response contains error
        self.assertContains(
            response,
            (
                "Maximum value: "
                f"{settings.SITE_SETTINGS['max_expiry_offset']['max_value']}"
            ),
        )

        # Check that the setting was not changed
        self.assertEqual(
            SiteSetting.get_setting("max_expiry_offset"),
            old_setting_max_expiry_offset,
        )


class SiteSettingsSiteInformationTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.super_user = User.objects.create_user(
            TEST_USER_EMAIL, TEST_USER_PASSWORD, is_staff=True
        )

    def test_site_information(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse("shifter_site_settings:site-settings")
        test_startup_time = timezone.now() - timezone.timedelta(minutes=5)
        with self.settings(STARTUP_TIME=test_startup_time):
            response = client.get(url)

            self.assertContains(
                response,
                '<p class="font-semibold">Debug Mode</p><p class="font-black text-4xl text-primary">False</p>',  # noqa: E501
                html=True,
            )
            self.assertContains(
                response,
                '<p class="font-semibold">Shifter Version</p><p class="font-black text-4xl text-primary">TESTING</p>',  # noqa: E501
                html=True,
            )
            self.assertContains(
                response,
                f'<p class="font-semibold">Python Version</p><p class="font-black text-4xl text-primary">{os.environ.get("PYTHON_VERSION")}</p>',  # noqa: E501
                html=True,
            )
            self.assertContains(
                response,
                '<p class="font-semibold">DB Engine</p><p class="font-black text-4xl text-primary">SQLITE</p>',  # noqa: E501
                html=True,
            )
            # Contains a non-breaking space which breaks the assertContains.
            self.assertRegex(
                response.content.decode("utf-8"),
                re.compile(
                    r'<p class="font-semibold">Uptime</p>\n\s+<p class="font-black text-4xl text-primary">5\xa0minutes</p>',  # noqa: E501
                    re.UNICODE,
                ),
            )
            self.assertContains(
                response,
                '<p class="font-semibold">Active Files</p><p class="font-black text-4xl text-primary">0</p>',  # noqa: E501
                html=True,
            )


class SiteSettingFieldTypesTestCase(TestCase):
    """Test different field types and conversions for site settings."""

    def setUp(self):
        """Initialize test settings."""
        # Create test users
        User = get_user_model()
        User.objects.create_user(
            email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD, is_staff=True
        )
        # Initialize settings from defaults
        call_command("createsettings")

    def test_boolean_setting_default_value(self):
        """Test that boolean setting returns correct default value."""
        # Should return boolean False, not string "False"
        result = SiteSetting.get_setting("allow_optional_expiry")
        self.assertIsInstance(result, bool)
        self.assertEqual(result, False)

    def test_boolean_setting_string_true_conversion(self):
        """Test that string 'True' converts to boolean True."""
        setting = SiteSetting.objects.get(name="allow_optional_expiry")
        setting.value = "True"
        setting.save()

        result = SiteSetting.get_setting("allow_optional_expiry")
        self.assertIsInstance(result, bool)
        self.assertEqual(result, True)

    def test_boolean_setting_string_false_conversion(self):
        """Test that string 'False' converts to boolean False."""
        setting = SiteSetting.objects.get(name="allow_optional_expiry")
        setting.value = "False"
        setting.save()

        result = SiteSetting.get_setting("allow_optional_expiry")
        self.assertIsInstance(result, bool)
        self.assertEqual(result, False)

    def test_boolean_setting_case_insensitive(self):
        """Test that boolean conversion is case-insensitive."""
        setting = SiteSetting.objects.get(name="allow_optional_expiry")

        # Test various casings
        for value in ["true", "TRUE", "True", "tRuE"]:
            setting.value = value
            setting.save()
            result = SiteSetting.get_setting("allow_optional_expiry")
            self.assertEqual(result, True, f"Failed for value: {value}")

    def test_boolean_setting_numeric_one_is_true(self):
        """Test that string '1' converts to boolean True."""
        setting = SiteSetting.objects.get(name="allow_optional_expiry")
        setting.value = "1"
        setting.save()

        result = SiteSetting.get_setting("allow_optional_expiry")
        self.assertEqual(result, True)

    def test_boolean_setting_other_values_are_false(self):
        """Test that non-true values convert to boolean False."""
        setting = SiteSetting.objects.get(name="allow_optional_expiry")

        # Test various "falsy" strings
        for value in ["0", "false", "FALSE", "no", "off", ""]:
            setting.value = value
            setting.save()
            result = SiteSetting.get_setting("allow_optional_expiry")
            self.assertEqual(result, False, f"Failed for value: {value}")

    def test_char_field_returns_string(self):
        """Test that CharField setting returns string value."""
        result = SiteSetting.get_setting("max_file_size")
        self.assertIsInstance(result, str)
        self.assertEqual(result, "5120MB")

    def test_int_field_returns_string(self):
        """Test that IntegerField setting returns string."""
        # Note: IntegerField values are stored as strings
        # Conversion happens in the consuming code
        result = SiteSetting.get_setting("default_expiry_offset")
        self.assertIsInstance(result, str)
        # Verify it can be converted to int
        self.assertEqual(int(result), 24 * 14)

    def test_boolean_form_field_initial_true(self):
        """Test boolean form field initializes with True."""
        setting = SiteSetting.objects.get(name="allow_optional_expiry")
        setting.value = "True"
        setting.save()

        form = SiteSettingsForm()
        field = form.fields["setting_allow_optional_expiry"]

        self.assertIsInstance(field, forms.BooleanField)
        self.assertEqual(field.initial, True)
        self.assertEqual(field.required, False)

    def test_boolean_form_field_initial_false(self):
        """Test boolean form field initializes with False."""
        setting = SiteSetting.objects.get(name="allow_optional_expiry")
        setting.value = "False"
        setting.save()

        form = SiteSettingsForm()
        field = form.fields["setting_allow_optional_expiry"]

        self.assertEqual(field.initial, False)

    def test_boolean_view_save_checked(self):
        """Test that checking boolean toggle saves as 'True'."""
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)

        # Submit form with checkbox checked (True)
        response = client.post(
            reverse("shifter_site_settings:site-settings"),
            {
                "setting_max_file_size": "5120MB",
                "setting_default_expiry_offset": str(24 * 14),
                "setting_max_expiry_offset": str(24 * 365 * 5),
                "setting_allow_optional_expiry": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        setting = SiteSetting.objects.get(name="allow_optional_expiry")
        # Should be stored as string "True"
        self.assertEqual(setting.value, "True")
        # get_setting should return boolean True
        self.assertEqual(
            SiteSetting.get_setting("allow_optional_expiry"), True
        )

    def test_boolean_view_save_unchecked(self):
        """Test that unchecking boolean toggle saves as 'False'."""
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)

        # First set to True
        setting = SiteSetting.objects.get(name="allow_optional_expiry")
        setting.value = "True"
        setting.save()

        # Submit form with checkbox unchecked (omitted from POST data)
        response = client.post(
            reverse("shifter_site_settings:site-settings"),
            {
                "setting_max_file_size": "5120MB",
                "setting_default_expiry_offset": str(24 * 14),
                "setting_max_expiry_offset": str(24 * 365 * 5),
                # setting_allow_optional_expiry omitted = unchecked
            },
        )

        self.assertEqual(response.status_code, 200)
        setting.refresh_from_db()
        # Should be stored as string "False"
        self.assertEqual(setting.value, "False")
        # get_setting should return boolean False
        self.assertEqual(
            SiteSetting.get_setting("allow_optional_expiry"), False
        )

    def test_boolean_form_renders_checkbox_widget(self):
        """Test that boolean field uses checkbox widget in form."""
        form = SiteSettingsForm()
        field = form.fields["setting_allow_optional_expiry"]

        # Check widget type
        self.assertEqual(field.widget.input_type, "checkbox")

    def test_all_setting_types_persist_correctly(self):
        """Integration test: all field types save and retrieve."""
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)

        # Submit form with all fields
        response = client.post(
            reverse("shifter_site_settings:site-settings"),
            {
                "setting_max_file_size": "10240MB",  # CharField
                "setting_default_expiry_offset": "720",  # IntegerField
                "setting_max_expiry_offset": "87600",  # IntegerField
                "setting_allow_optional_expiry": "on",  # BooleanField
            },
        )

        self.assertEqual(response.status_code, 200)

        # Verify CharField
        self.assertEqual(SiteSetting.get_setting("max_file_size"), "10240MB")

        # Verify IntegerField (returns string)
        self.assertEqual(
            SiteSetting.get_setting("default_expiry_offset"), "720"
        )

        # Verify BooleanField (returns boolean)
        self.assertEqual(
            SiteSetting.get_setting("allow_optional_expiry"), True
        )
