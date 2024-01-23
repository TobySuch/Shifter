from io import StringIO

from django.test import TestCase, Client
from django.conf import settings
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.urls import reverse

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
        domain = SiteSetting.objects.get(name="domain")
        self.assertEqual(
            domain.value, settings.SITE_SETTINGS["domain"]["default"]
        )

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
        new_domain = "testdomain.com"
        response = client.post(
            url,
            {
                "setting_domain": new_domain,
                "setting_max_file_size": "100MB",
                "setting_default_expiry_offset": "1",
                "setting_max_expiry_offset": "2",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SiteSetting.get_setting("domain"), new_domain)
        self.assertEqual(SiteSetting.get_setting("max_file_size"), "100MB")
        self.assertEqual(SiteSetting.get_setting("default_expiry_offset"), "1")
        self.assertEqual(SiteSetting.get_setting("max_expiry_offset"), "2")

    def test_standard_user_cannot_access(self):
        # Test that a standard user cannot access the site settings page
        client = Client()
        client.login(email=TEST_USER_EMAIL_2, password=TEST_USER_PASSWORD_2)
        url = reverse("shifter_site_settings:site-settings")
        response = client.get(url)
        self.assertEqual(response.status_code, 403)
