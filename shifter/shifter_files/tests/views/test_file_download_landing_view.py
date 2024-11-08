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

TEST_USER_EMAIL = "iama@test.com"
TEST_USER_PASSWORD = "mytemporarypassword"

TEST_USER_EMAIL_2 = "shifter@github.com"
TEST_USER_PASSWORD_2 = "mytemporarypassword"

TEST_FILE_NAME = "mytestfile.txt"
TEST_FILE_CONTENT = b"Hello, World!"


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class FileDownloadLandingViewTest(TestCase):
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

    def test_unauthenticated_get(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        file_upload = FileUpload.objects.create(
            owner=self.user,
            file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() + datetime.timedelta(weeks=1),
            filename=TEST_FILE_NAME,
        )
        client_unauthenticated = Client()
        url = reverse(
            "shifter_files:file-download-landing", args=[file_upload.file_hex]
        )
        response = client_unauthenticated.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "shifter_files/file_download_landing.html"
        )
        self.assertInHTML(
            f"You are downloading: {TEST_FILE_NAME}", response.content.decode()
        )

    def test_different_user(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        file_upload = FileUpload.objects.create(
            owner=self.user,
            file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() + datetime.timedelta(weeks=1),
            filename=TEST_FILE_NAME,
        )
        client_2 = Client()
        client_2.login(email=TEST_USER_EMAIL_2, password=TEST_USER_PASSWORD_2)
        url = reverse(
            "shifter_files:file-download-landing", args=[file_upload.file_hex]
        )
        response = client_2.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "shifter_files/file_download_landing.html"
        )
        self.assertInHTML(
            f"You are downloading: {TEST_FILE_NAME}", response.content.decode()
        )

    def test_file_owner_user(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        file_upload = FileUpload.objects.create(
            owner=self.user,
            file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() + datetime.timedelta(weeks=1),
            filename=TEST_FILE_NAME,
        )
        url = reverse(
            "shifter_files:file-download-landing", args=[file_upload.file_hex]
        )
        response = client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "shifter_files/file_download_landing.html"
        )
        self.assertInHTML(
            f"You are downloading: {TEST_FILE_NAME}", response.content.decode()
        )

    def test_file_does_not_exist(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse("shifter_files:file-download-landing", args=["0" * 32])
        response = client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_expired_file(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        file_upload = FileUpload.objects.create(
            owner=self.user,
            file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() - datetime.timedelta(days=1),
            filename=TEST_FILE_NAME,
        )
        url = reverse(
            "shifter_files:file-download-landing", args=[file_upload.file_hex]
        )
        response = client.get(url)

        self.assertEqual(response.status_code, 404)
