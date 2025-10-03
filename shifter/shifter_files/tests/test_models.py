import datetime
import pathlib
import tempfile
from shutil import rmtree

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from shifter_files.models import FileUpload

TEST_USER_EMAIL = "iama@test.com"
TEST_USER_PASSWORD = "mytemporarypassword"

TEST_FILE_NAME = "mytestfile.txt"
TEST_FILE_CONTENT = b"Hello, World!"


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class FileUploadModelTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            TEST_USER_EMAIL, TEST_USER_PASSWORD
        )

    def tearDown(self):
        rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def test_add_new_file(self):
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        current_datetime = timezone.now()
        expiry_datetime = current_datetime + datetime.timedelta(days=1)
        file_upload = FileUpload.objects.create(
            owner=self.user,
            file_content=test_file,
            upload_datetime=current_datetime,
            expiry_datetime=expiry_datetime,
            filename=TEST_FILE_NAME,
        )

        self.assertEqual(FileUpload.objects.count(), 1)
        file_upload = FileUpload.objects.first()
        self.assertEqual(file_upload.filename, TEST_FILE_NAME)
        self.assertEqual(file_upload.owner, self.user)
        self.assertAlmostEqual(
            file_upload.upload_datetime,
            current_datetime,
            delta=datetime.timedelta(minutes=1),
        )
        self.assertAlmostEqual(
            file_upload.expiry_datetime,
            expiry_datetime,
            delta=datetime.timedelta(minutes=1),
        )
        # Ensure file has been uploaded to the correct location
        path = pathlib.Path(settings.MEDIA_ROOT + "/uploads/" + TEST_FILE_NAME)
        self.assertTrue(path.is_file())

    def test_is_expired_false(self):
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        current_datetime = timezone.now()
        expiry_datetime = current_datetime + datetime.timedelta(days=1)
        file_upload = FileUpload.objects.create(
            owner=self.user,
            file_content=test_file,
            upload_datetime=current_datetime,
            expiry_datetime=expiry_datetime,
            filename=TEST_FILE_NAME,
        )

        self.assertFalse(file_upload.is_expired())

    def test_is_expired_true(self):
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        current_datetime = timezone.now()
        expiry_datetime = current_datetime - datetime.timedelta(days=1)
        file_upload = FileUpload.objects.create(
            owner=self.user,
            file_content=test_file,
            upload_datetime=current_datetime,
            expiry_datetime=expiry_datetime,
            filename=TEST_FILE_NAME,
        )

        self.assertTrue(file_upload.is_expired())

    def test_is_expired_none(self):
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        current_datetime = timezone.now()
        file_upload = FileUpload.objects.create(
            owner=self.user,
            file_content=test_file,
            upload_datetime=current_datetime,
            expiry_datetime=None,
            filename=TEST_FILE_NAME,
        )

        self.assertFalse(file_upload.is_expired())

    def test_get_expired_files(self):
        expired_files = FileUpload.get_expired_files()
        self.assertEqual(expired_files.count(), 0)

        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        current_datetime = timezone.now()
        expiry_datetime = current_datetime - datetime.timedelta(days=1)
        file_upload = FileUpload.objects.create(
            owner=self.user,
            file_content=test_file,
            upload_datetime=current_datetime,
            expiry_datetime=expiry_datetime,
            filename=TEST_FILE_NAME,
        )

        expired_files = FileUpload.get_expired_files()
        self.assertEqual(expired_files.count(), 1)
        self.assertEqual(expired_files.first(), file_upload)

        file_upload2 = FileUpload.objects.create(
            owner=self.user,
            file_content=test_file,
            upload_datetime=current_datetime,
            expiry_datetime=expiry_datetime,
            filename=TEST_FILE_NAME,
        )

        expired_files = FileUpload.get_expired_files()
        self.assertEqual(expired_files.count(), 2)
        self.assertEqual(expired_files.last(), file_upload2)

    def test_get_expired_files_ignores_non_expiring(self):
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        current_datetime = timezone.now()

        FileUpload.objects.create(
            owner=self.user,
            file_content=test_file,
            upload_datetime=current_datetime,
            expiry_datetime=None,
            filename=TEST_FILE_NAME,
        )

        expired_files = FileUpload.get_expired_files()
        self.assertEqual(expired_files.count(), 0)

    def test_delete_expired_files_empty(self):
        self.assertEqual(FileUpload.get_expired_files().count(), 0)
        num_files_deleted = FileUpload.delete_expired_files()
        self.assertEqual(num_files_deleted, 0)

    def test_delete_expired_files(self):
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        current_datetime = timezone.now()
        expiry_datetime = current_datetime - datetime.timedelta(days=1)

        for _ in range(2):
            FileUpload.objects.create(
                owner=self.user,
                file_content=test_file,
                upload_datetime=current_datetime,
                expiry_datetime=expiry_datetime,
                filename=TEST_FILE_NAME,
            )

        self.assertEqual(FileUpload.get_expired_files().count(), 2)
        num_files_deleted = FileUpload.delete_expired_files()
        self.assertEqual(num_files_deleted, 2)
        self.assertEqual(FileUpload.get_expired_files().count(), 0)

    def test_get_non_expired_files_includes_non_expiring(self):
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        current_datetime = timezone.now()
        future_datetime = current_datetime + datetime.timedelta(days=1)

        future_file = FileUpload.objects.create(
            owner=self.user,
            file_content=test_file,
            upload_datetime=current_datetime,
            expiry_datetime=future_datetime,
            filename=TEST_FILE_NAME,
        )
        non_expiring_file = FileUpload.objects.create(
            owner=self.user,
            file_content=test_file,
            upload_datetime=current_datetime,
            expiry_datetime=None,
            filename=TEST_FILE_NAME,
        )
        FileUpload.objects.create(
            owner=self.user,
            file_content=test_file,
            upload_datetime=current_datetime,
            expiry_datetime=current_datetime - datetime.timedelta(days=1),
            filename=TEST_FILE_NAME,
        )

        non_expired = list(FileUpload.get_non_expired_files())

        self.assertIn(future_file, non_expired)
        self.assertIn(non_expiring_file, non_expired)
        self.assertEqual(len(non_expired), 2)
