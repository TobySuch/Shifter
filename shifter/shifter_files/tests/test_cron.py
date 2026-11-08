import datetime
import pathlib
import tempfile
from shutil import rmtree

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from shifter_files.cron import delete_expired_files
from shifter_files.models import ChunkedUpload, FileUpload

TEST_USER_EMAIL = "iama@test.com"
TEST_USER_PASSWORD = "mytemporarypassword"

TEST_FILE_NAME = "mytestfile.txt"
TEST_FILE_CONTENT = b"Hello, World!"


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class DeleteExpiredFilesTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            TEST_USER_EMAIL, TEST_USER_PASSWORD
        )

    def tearDown(self):
        rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def test_expired_file_delete(self):
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        FileUpload.objects.create(
            owner=self.user,
            file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() - datetime.timedelta(days=1),
            filename=TEST_FILE_NAME,
        )

        path = pathlib.Path("media/uploads/" + TEST_FILE_NAME)

        # Run cron job
        delete_expired_files()

        # Ensure file has been deleted from db && uploads folder
        self.assertEqual(FileUpload.objects.count(), 0)
        self.assertFalse(path.is_file())


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class DeleteStaleChunkedUploadsTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            TEST_USER_EMAIL, TEST_USER_PASSWORD
        )

    def tearDown(self):
        rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def make_upload(self, age_hours):
        upload = ChunkedUpload.objects.create(
            owner=self.user, filename="partial.bin", total_size=10
        )
        upload.create_temp_file()
        # updated_at is auto_now, so backdate it with a queryset update.
        ChunkedUpload.objects.filter(pk=upload.pk).update(
            updated_at=timezone.now() - datetime.timedelta(hours=age_hours)
        )
        return upload

    @override_settings(CHUNKED_UPLOAD_MAX_AGE_HOURS=24)
    def test_delete_stale_removes_old_uploads_and_temp_files(self):
        stale = self.make_upload(age_hours=25)
        fresh = self.make_upload(age_hours=1)

        self.assertEqual(ChunkedUpload.delete_stale(), 1)

        self.assertFalse(ChunkedUpload.objects.filter(pk=stale.pk).exists())
        self.assertFalse(pathlib.Path(stale.temp_path).exists())
        self.assertTrue(ChunkedUpload.objects.filter(pk=fresh.pk).exists())
        self.assertTrue(pathlib.Path(fresh.temp_path).exists())

    def test_delete_stale_tolerates_missing_temp_file(self):
        stale = self.make_upload(age_hours=48)
        pathlib.Path(stale.temp_path).unlink()

        self.assertEqual(ChunkedUpload.delete_stale(), 1)

    def test_cron_job_deletes_stale_uploads(self):
        stale = self.make_upload(age_hours=48)

        delete_expired_files()

        self.assertFalse(ChunkedUpload.objects.filter(pk=stale.pk).exists())
