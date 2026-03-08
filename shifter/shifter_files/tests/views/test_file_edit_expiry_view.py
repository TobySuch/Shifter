import datetime
import tempfile
from shutil import rmtree

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
class FileEditExpiryViewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            TEST_USER_EMAIL, TEST_USER_PASSWORD
        )
        self.user_2 = User.objects.create_user(
            TEST_USER_EMAIL_2, TEST_USER_PASSWORD_2
        )

    def tearDown(self):
        rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def _create_file(self, owner=None, expiry_offset_weeks=1):
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        if owner is None:
            owner = self.user
        kwargs = {
            "owner": owner,
            "file_content": test_file,
            "upload_datetime": timezone.now(),
            "filename": TEST_FILE_NAME,
        }
        if expiry_offset_weeks is not None:
            kwargs["expiry_datetime"] = timezone.now() + datetime.timedelta(
                weeks=expiry_offset_weeks
            )
        return FileUpload.objects.create(**kwargs)

    # --- Auth / access ---

    def test_unauthenticated_get_redirects(self):
        file_upload = self._create_file()
        url = reverse(
            "shifter_files:file-edit-expiry", args=[file_upload.file_hex]
        )
        response = Client().get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.url)

    def test_unauthenticated_post_redirects(self):
        file_upload = self._create_file()
        url = reverse(
            "shifter_files:file-edit-expiry", args=[file_upload.file_hex]
        )
        response = Client().post(url, {})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.url)

    def test_wrong_user_get_returns_404(self):
        file_upload = self._create_file(owner=self.user)
        client = Client()
        client.login(email=TEST_USER_EMAIL_2, password=TEST_USER_PASSWORD_2)
        url = reverse(
            "shifter_files:file-edit-expiry", args=[file_upload.file_hex]
        )
        response = client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_missing_hex_returns_404(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_files:file-edit-expiry", args=["0" * 32]
        )
        response = client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_expired_file_returns_404(self):
        file_upload = self._create_file(expiry_offset_weeks=-1)
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_files:file-edit-expiry", args=[file_upload.file_hex]
        )
        response = client.get(url)
        self.assertEqual(response.status_code, 404)

    # --- GET ---

    def test_get_renders_200_with_correct_template(self):
        file_upload = self._create_file()
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_files:file-edit-expiry", args=[file_upload.file_hex]
        )
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "shifter_files/fileupload_edit_expiry.html"
        )

    def test_get_no_expiry_file_renders_200(self):
        file_upload = self._create_file(expiry_offset_weeks=None)
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_files:file-edit-expiry", args=[file_upload.file_hex]
        )
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    # --- POST valid ---

    def test_post_valid_future_date_saves_and_redirects(self):
        file_upload = self._create_file()
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_files:file-edit-expiry", args=[file_upload.file_hex]
        )
        new_expiry = timezone.now() + datetime.timedelta(days=3)
        new_expiry_str = new_expiry.strftime(
            settings.DATETIME_INPUT_FORMATS[0]
        )
        response = client.post(
            url,
            {
                "enable_expiry": "on",
                "expiry_datetime": new_expiry_str,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(file_upload.file_hex, response.url)
        file_upload.refresh_from_db()
        self.assertIsNotNone(file_upload.expiry_datetime)

    def test_post_clear_expiry_when_allow_optional(self):
        SiteSetting.objects.update_or_create(
            name="allow_optional_expiry", defaults={"value": "True"}
        )
        file_upload = self._create_file()
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_files:file-edit-expiry", args=[file_upload.file_hex]
        )
        # enable_expiry not sent → False
        response = client.post(url, {"enable_expiry": ""})
        self.assertEqual(response.status_code, 302)
        file_upload.refresh_from_db()
        self.assertIsNone(file_upload.expiry_datetime)

    # --- POST invalid ---

    def test_post_past_date_rerenders_with_error(self):
        file_upload = self._create_file()
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_files:file-edit-expiry", args=[file_upload.file_hex]
        )
        past_expiry = timezone.now() - datetime.timedelta(days=1)
        past_expiry_str = past_expiry.strftime(
            settings.DATETIME_INPUT_FORMATS[0]
        )
        response = client.post(
            url,
            {
                "enable_expiry": "on",
                "expiry_datetime": past_expiry_str,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "expiry_datetime",
            "You can't set an expiry time in the past.",
        )

    def test_post_blank_date_when_required_rerenders_with_error(self):
        file_upload = self._create_file()
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_files:file-edit-expiry", args=[file_upload.file_hex]
        )
        response = client.post(
            url,
            {
                "enable_expiry": "on",
                "expiry_datetime": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "expiry_datetime",
            "You must provide an expiry date.",
        )

    # --- Settings interactions ---

    def test_allow_optional_expiry_shows_checkbox(self):
        SiteSetting.objects.update_or_create(
            name="allow_optional_expiry", defaults={"value": "True"}
        )
        file_upload = self._create_file()
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_files:file-edit-expiry", args=[file_upload.file_hex]
        )
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertNotEqual(
            form.fields["enable_expiry"].widget.__class__.__name__,
            "HiddenInput",
        )

    def test_disallow_optional_expiry_hides_checkbox(self):
        SiteSetting.objects.update_or_create(
            name="allow_optional_expiry", defaults={"value": "False"}
        )
        file_upload = self._create_file()
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_files:file-edit-expiry", args=[file_upload.file_hex]
        )
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(
            form.fields["enable_expiry"].widget.__class__.__name__,
            "HiddenInput",
        )

    def test_cannot_clear_expiry_when_setting_disabled(self):
        SiteSetting.objects.update_or_create(
            name="allow_optional_expiry", defaults={"value": "False"}
        )
        file_upload = self._create_file()
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_files:file-edit-expiry", args=[file_upload.file_hex]
        )
        # Attempt to POST without enable_expiry — should be ignored
        # since optional expiry is disabled, expiry_datetime is required
        response = client.post(
            url, {"enable_expiry": "", "expiry_datetime": ""}
        )
        self.assertEqual(response.status_code, 200)
        # File expiry should not be cleared
        file_upload.refresh_from_db()
        self.assertIsNotNone(file_upload.expiry_datetime)
