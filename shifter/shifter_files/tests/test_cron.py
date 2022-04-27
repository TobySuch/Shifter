import datetime
import pathlib
from shutil import rmtree

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

from shifter_files.models import FileUpload
from shifter_files.cron import delete_expired_files


TEST_USER_EMAIL = "iama@test.com"
TEST_USER_PASSWORD = "mytemporarypassword"

TEST_FILE_NAME = "mytestfile.txt"
TEST_FILE_CONTENT = b"Hello, World!"


class DeleteExpiredFilesTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(TEST_USER_EMAIL,
                                             TEST_USER_PASSWORD)

    def tearDown(self):
        rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def test_expired_file_delete(self):
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() - datetime.timedelta(days=1),
            filename=TEST_FILE_NAME)

        path = pathlib.Path("media/uploads/" + TEST_FILE_NAME)

        # Run cron job
        delete_expired_files()

        # Ensure file has been deleted from db && uploads folder
        self.assertEqual(FileUpload.objects.count(), 0)
        self.assertFalse(path.is_file())
