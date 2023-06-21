from io import StringIO
import datetime
from shutil import rmtree

from django.core.management import call_command
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

from shifter_files.models import FileUpload

TEST_USER_EMAIL = "iama@test.com"
TEST_USER_PASSWORD = "mytemporarypassword"

TEST_FILE_NAME = "mytestfile.txt"
TEST_FILE_CONTENT = b"Hello, World!"


class CleanUpExpiredCommandTest(TestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(TEST_USER_EMAIL,
                                             TEST_USER_PASSWORD)

    def tearDown(self):
        rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def command_output(self, *args, **kwargs):
        out = StringIO()
        call_command(
            'cleanupexpired',
            *args + ("--no-color",),
            stdout=out,
            stderr=StringIO(),
            **kwargs)
        return out.getvalue()

    def test_expired_files(self):
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() - datetime.timedelta(days=1),
            filename=TEST_FILE_NAME)

        out = self.command_output()
        self.assertIn(
            out,
            'Successfully deleted 1 expired file(s)\n')

    def test_no_expired_files(self):
        out = self.command_output()
        self.assertIn(
            out,
            'No expired files to be deleted\n')
