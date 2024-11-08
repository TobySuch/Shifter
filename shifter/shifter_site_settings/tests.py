import os
import re
from io import StringIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

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
