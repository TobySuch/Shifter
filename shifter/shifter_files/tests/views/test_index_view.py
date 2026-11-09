import datetime
import json
import re
import tempfile
from shutil import rmtree
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from shifter_files.models import FileUpload
from shifter_site_settings.models import SiteSetting

TEST_USER_EMAIL = "iama@test.com"
TEST_USER_PASSWORD = "mytemporarypassword"

TEST_USER_EMAIL_2 = "shifter@github.com"
TEST_USER_PASSWORD_2 = "mytemporarypassword"

TEST_FILE_NAME = "mytestfile.txt"
TEST_FILE_CONTENT = b"Hello, World!"


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class IndexViewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            TEST_USER_EMAIL, TEST_USER_PASSWORD
        )

    def tearDown(self):
        rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def test_force_authentication(self):
        client = Client()
        url = reverse("shifter_files:index")
        response = client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response.url, reverse("shifter_auth:login") + "?next=" + url
        )

    def test_upload_page_rejects_post(self):
        """Uploads go through the chunked API; the page itself is GET only."""
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.post(
            reverse("shifter_files:index"),
            {
                "expiry_datetime": (
                    timezone.now() + datetime.timedelta(days=1)
                ).isoformat(sep=" ", timespec="minutes"),
                "file_content": SimpleUploadedFile(
                    TEST_FILE_NAME, TEST_FILE_CONTENT
                ),
            },
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(FileUpload.objects.count(), 0)

    def test_authenticated_user_not_redirected(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_files:index"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "shifter_files/file_upload.html")

    # #427 - Setting max expiry date in hours to large number causes 500 error
    # when accessing file upload page.
    def test_site_setting_max_expiry_too_big(self):
        SiteSetting.objects.create(
            name="max_expiry_offset",
            value="2147483647",
        )

        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse("shifter_files:index")
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_context_contains_upload_timeout_default(self):
        """Test that upload page context includes the default timeout."""
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_files:index"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("setting_upload_timeout", response.context)
        self.assertEqual(
            response.context["setting_upload_timeout"],
            settings.UPLOAD_TIMEOUT,
        )

    @override_settings(UPLOAD_TIMEOUT=900)
    def test_context_contains_custom_upload_timeout(self):
        """Test that a custom UPLOAD_TIMEOUT is passed to context."""
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_files:index"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["setting_upload_timeout"], 900)

    def _get_rendered_upload_props(self, response):
        match = re.search(
            r'<script id="upload-props" type="application/json">'
            r"(.*?)</script>",
            response.content.decode(),
            re.DOTALL,
        )
        self.assertIsNotNone(match, "upload-props json_script not rendered")
        return json.loads(match.group(1))

    def test_upload_timeout_in_template(self):
        """Test that the upload timeout is rendered in the island props."""
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_files:index"))
        props = self._get_rendered_upload_props(response)
        self.assertEqual(props["uploadTimeout"], settings.UPLOAD_TIMEOUT)

    def test_upload_island_mount_point_in_template(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_files:index"))
        self.assertContains(
            response,
            'data-react-island="UploadPage" data-props-id="upload-props"',
        )
        # The CSRF token input is still rendered for the island to read.
        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    @mock.patch(
        "django.utils.timezone.now",
        return_value=datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.UTC),
    )
    def test_upload_props_defaults(self, _mock_now):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_files:index"))
        props = self._get_rendered_upload_props(response)

        default_offset = int(
            settings.SITE_SETTINGS["default_expiry_offset"]["default"]
        )
        max_offset = int(
            settings.SITE_SETTINGS["max_expiry_offset"]["default"]
        )
        now = timezone.now()
        self.assertEqual(
            props,
            {
                "initUrl": reverse("shifter_files:chunked-upload-init"),
                "fileFieldName": "file_content",
                "maxFileSize": settings.SITE_SETTINGS["max_file_size"][
                    "default"
                ],
                "uploadTimeout": settings.UPLOAD_TIMEOUT,
                # A real boolean: the "False" default string would be
                # truthy in JavaScript.
                "allowOptionalExpiry": False,
                "expiry": {
                    "initial": (
                        now + datetime.timedelta(hours=default_offset)
                    ).isoformat(),
                    "min": now.isoformat(),
                    "max": (
                        now + datetime.timedelta(hours=max_offset)
                    ).isoformat(),
                },
            },
        )
        self.assertEqual(response.context["upload_props"], props)

    def test_upload_props_reflect_site_settings(self):
        SiteSetting.objects.create(name="max_file_size", value="12MB")
        SiteSetting.objects.create(name="allow_optional_expiry", value="True")
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_files:index"))
        props = self._get_rendered_upload_props(response)
        self.assertEqual(props["maxFileSize"], "12MB")
        self.assertIs(props["allowOptionalExpiry"], True)

    def test_upload_props_max_expiry_none_when_offset_overflows(self):
        SiteSetting.objects.create(
            name="max_expiry_offset",
            value="2147483647",
        )
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_files:index"))
        props = self._get_rendered_upload_props(response)
        self.assertIsNone(props["expiry"]["max"])

