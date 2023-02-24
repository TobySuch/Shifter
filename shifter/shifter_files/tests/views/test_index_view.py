import datetime
import pathlib
from shutil import rmtree
import json

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

from shifter_files.models import FileUpload

TEST_USER_EMAIL = "iama@test.com"
TEST_USER_PASSWORD = "mytemporarypassword"

TEST_USER_EMAIL_2 = "shifter@github.com"
TEST_USER_PASSWORD_2 = "mytemporarypassword"

TEST_FILE_NAME = "mytestfile.txt"
TEST_FILE_CONTENT = b"Hello, World!"


class IndexViewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(TEST_USER_EMAIL,
                                             TEST_USER_PASSWORD)

    def tearDown(self):
        rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def test_force_authentication(self):
        client = Client()
        url = reverse("shifter_files:index")
        response = client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url,
                        reverse("shifter_auth:login") + "?next=" + url)

    def test_authenticated_user_not_redirected(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_files:index"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue("<h1 class=\"title\">Upload File</h1>")

    def test_file_upload(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        current_datetime = timezone.now()
        expiry_datetime = current_datetime + datetime.timedelta(days=1)
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        response = client.post(reverse("shifter_files:index"), {
            "expiry_datetime": expiry_datetime.isoformat(
                sep=' ', timespec='minutes'),
            "file_content": test_file
        })
        self.assertEqual(response.status_code, 200)

        self.assertEqual(FileUpload.objects.count(), 1)
        file_upload = FileUpload.objects.first()
        self.assertEqual(file_upload.filename, TEST_FILE_NAME)
        self.assertEqual(file_upload.owner, self.user)
        self.assertAlmostEqual(file_upload.upload_datetime, current_datetime,
                               delta=datetime.timedelta(minutes=1))
        self.assertAlmostEqual(file_upload.expiry_datetime, expiry_datetime,
                               delta=datetime.timedelta(minutes=1))
        # Ensure file has been uploaded to the correct location
        path = pathlib.Path("media/uploads/" + TEST_FILE_NAME + "_"
                            + file_upload.file_hex)
        self.assertTrue(path.is_file())

        expected_response = {
            "redirect_url": reverse("shifter_files:file-details",
                                    args=[file_upload.file_hex])
        }
        self.assertEqual(
            json.dumps(expected_response),
            response.content.decode())

    def test_expiry_date_in_past(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        current_datetime = timezone.now()
        expiry_datetime = current_datetime - datetime.timedelta(days=1)
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        response = client.post(reverse("shifter_files:index"), {
            "expiry_datetime": expiry_datetime.isoformat(
                sep=' ', timespec='minutes'),
            "file_content": test_file
        })
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content.decode(), {
            'errors': {
                'expiry_datetime': ["You can't upload a file with an expiry "
                                    + "time in the past!"]
            }
        })
        self.assertEqual(FileUpload.objects.count(), 0)

    def test_file_upload_unauthenticated(self):
        client = Client()
        current_datetime = timezone.now()
        expiry_datetime = current_datetime + datetime.timedelta(days=1)
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        response = client.post(reverse("shifter_files:index"), {
            "expiry_datetime": expiry_datetime.isoformat(
                sep=' ', timespec='minutes'),
            "file_content": test_file
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FileUpload.objects.count(), 0)
