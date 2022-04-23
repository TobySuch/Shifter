import datetime
import pathlib

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from shifter_files.models import FileUpload

TEST_USER_EMAIL = "iama@test.com"
TEST_USER_PASSWORD = "mytemporarypassword"


class IndexViewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(TEST_USER_EMAIL,
                                             TEST_USER_PASSWORD)

    def test_force_authentication(self):
        client = Client()
        response = client.get(reverse("shifter_files:index"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url,
                        reverse("shifter_auth:login") + "?next=/")

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
        filename = "manage.py"
        with open(filename, 'rb') as fp:
            response = client.post(reverse("shifter_files:index"), {
                "expiry_datetime": expiry_datetime.isoformat(
                    sep=' ', timespec='minutes'),
                "file_content": fp
            })
        self.assertEqual(response.status_code, 302)

        self.assertEqual(FileUpload.objects.count(), 1)
        file_upload = FileUpload.objects.first()
        self.assertEqual(file_upload.filename, filename)
        self.assertEqual(file_upload.owner, self.user)
        self.assertAlmostEqual(file_upload.upload_datetime, current_datetime,
                               delta=datetime.timedelta(minutes=1))
        self.assertAlmostEqual(file_upload.expiry_datetime, expiry_datetime,
                               delta=datetime.timedelta(minutes=1))
        # Ensure file has been uploaded to the correct location
        path = pathlib.Path("media/uploads/" + filename)
        self.assertTrue(path.is_file())
