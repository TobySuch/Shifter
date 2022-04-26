import datetime
import pathlib

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

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

    def test_expired_file_delete(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        file_name = "mytestfile.txt"
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() - datetime.timedelta(days=1),
            filename=file_name)

        self.assertEqual(FileUpload.objects.count(), 1)
        path = pathlib.Path("media/uploads/" + file_name)
        self.assertTrue(path.is_file())

        # Run cron job
        delete_expired_files()

        # Ensure file has been deleted from db && uploads folder
        self.assertEqual(FileUpload.objects.count(), 0)
        self.assertFalse(path.is_file())
