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

        now = timezone.now()
        self.assertEqual(
            props,
            {
                "initUrl": reverse("shifter_files:chunked-upload-init"),
                "fileFieldName": "file_content",
                # 5GB, in bytes
                "maxFileSize": 5 * 1024**3,
                "uploadTimeout": settings.UPLOAD_TIMEOUT,
                # A real boolean: the "False" default string would be
                # truthy in JavaScript.
                "allowOptionalExpiry": False,
                "expiry": {
                    # Defaults: 2 weeks, with a maximum of 1 month.
                    "initial": "2026-01-15T12:00:00+00:00",
                    "min": now.isoformat(),
                    "max": "2026-02-01T12:00:00+00:00",
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
        self.assertEqual(props["maxFileSize"], 12 * 1024**2)
        self.assertIs(props["allowOptionalExpiry"], True)

    @mock.patch(
        "django.utils.timezone.now",
        return_value=datetime.datetime(2026, 1, 31, 9, 0, tzinfo=datetime.UTC),
    )
    def test_upload_props_use_expiry_offset_units(self, _mock_now):
        SiteSetting.objects.create(name="default_expiry_offset", value="3D")
        SiteSetting.objects.create(name="max_expiry_offset", value="1M")
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_files:index"))
        props = self._get_rendered_upload_props(response)
        self.assertEqual(
            props["expiry"]["initial"], "2026-02-03T09:00:00+00:00"
        )
        # A calendar month, clamped to the end of February.
        self.assertEqual(props["expiry"]["max"], "2026-02-28T09:00:00+00:00")

    def test_upload_props_offset_without_unit_is_hours(self):
        SiteSetting.objects.create(name="default_expiry_offset", value="5")
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        before = timezone.now()
        response = client.get(reverse("shifter_files:index"))
        props = self._get_rendered_upload_props(response)
        initial = datetime.datetime.fromisoformat(props["expiry"]["initial"])
        self.assertGreaterEqual(initial, before + datetime.timedelta(hours=5))
        self.assertLess(
            initial, before + datetime.timedelta(hours=5, minutes=1)
        )

    def test_upload_props_max_file_size_in_gb_is_bytes(self):
        SiteSetting.objects.create(name="max_file_size", value="2GB")
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_files:index"))
        props = self._get_rendered_upload_props(response)
        self.assertEqual(props["maxFileSize"], 2 * 1024**3)

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

