import datetime
import pathlib

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

from shifter_files.models import FileUpload
from shifter_files.cron import delete_expired_files

TEST_USER_EMAIL = "iama@test.com"
TEST_USER_PASSWORD = "mytemporarypassword"

TEST_USER_EMAIL_2 = "shifter@github.com"
TEST_USER_PASSWORD_2 = "mytemporarypassword"

TEST_FILE_PATH = "manage.py"


class IndexViewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(TEST_USER_EMAIL,
                                             TEST_USER_PASSWORD)

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
        with open(TEST_FILE_PATH, 'rb') as fp:
            response = client.post(reverse("shifter_files:index"), {
                "expiry_datetime": expiry_datetime.isoformat(
                    sep=' ', timespec='minutes'),
                "file_content": fp
            })
        self.assertEqual(response.status_code, 302)

        self.assertEqual(FileUpload.objects.count(), 1)
        file_upload = FileUpload.objects.first()
        self.assertEqual(file_upload.filename, TEST_FILE_PATH)
        self.assertEqual(file_upload.owner, self.user)
        self.assertAlmostEqual(file_upload.upload_datetime, current_datetime,
                               delta=datetime.timedelta(minutes=1))
        self.assertAlmostEqual(file_upload.expiry_datetime, expiry_datetime,
                               delta=datetime.timedelta(minutes=1))
        # Ensure file has been uploaded to the correct location
        path = pathlib.Path("media/uploads/" + TEST_FILE_PATH)
        self.assertTrue(path.is_file())

        self.assertEqual(response.url, reverse("shifter_files:file-details",
                                               args=[file_upload.file_hex]))

    def test_expired_file_delete(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        expiry_datetime = timezone.now() - datetime.timedelta(days=1)
        filename = "entrypoint.sh"
        with open(filename, 'rb') as fp:
            response = client.post(reverse("shifter_files:index"), {
                "expiry_datetime": expiry_datetime.isoformat(
                    sep=' ', timespec='minutes'),
                "file_content": fp
            })
        self.assertEqual(response.status_code, 302)

        self.assertEqual(FileUpload.objects.count(), 1)
        path = pathlib.Path("media/uploads/" + filename)
        self.assertTrue(path.is_file())

        # Run cron job
        delete_expired_files()

        # Ensure file has been deleted from db && uploads folder
        self.assertEqual(FileUpload.objects.count(), 0)
        self.assertFalse(path.is_file())


class FileDetailsViewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(TEST_USER_EMAIL,
                                             TEST_USER_PASSWORD)

        self.user_2 = User.objects.create_user(TEST_USER_EMAIL_2,
                                               TEST_USER_PASSWORD_2)

    def test_unauthenticated_get(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        test_file = SimpleUploadedFile("mytestfile.txt", b"Hello, World!")
        file_upload = FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() + datetime.timedelta(weeks=1),
            filename=TEST_FILE_PATH)
        client_unauthenticated = Client()
        url = reverse("shifter_files:file-details",
                      args=[file_upload.file_hex])
        response = client_unauthenticated.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url,
                        reverse("shifter_auth:login") + "?next=" + url)

    def test_different_user(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        test_file = SimpleUploadedFile("mytestfile.txt", b"Hello, World!")
        file_upload = FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() + datetime.timedelta(weeks=1),
            filename=TEST_FILE_PATH)
        client_2 = Client()
        client_2.login(email=TEST_USER_EMAIL_2, password=TEST_USER_PASSWORD_2)
        url = reverse("shifter_files:file-details",
                      args=[file_upload.file_hex])
        response = client_2.get(url)

        self.assertEqual(response.status_code, 404)

    def test_correct_user(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        test_file = SimpleUploadedFile("mytestfile.txt", b"Hello, World!")
        file_upload = FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() + datetime.timedelta(weeks=1),
            filename=TEST_FILE_PATH)
        url = reverse("shifter_files:file-details",
                      args=[file_upload.file_hex])
        response = client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_file_does_not_exist(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse("shifter_files:file-details",
                      args=['0'*32])
        response = client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_expired_file(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        test_file = SimpleUploadedFile("mytestfile.txt", b"Hello, World!")
        file_upload = FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() - datetime.timedelta(days=1),
            filename=TEST_FILE_PATH)
        url = reverse("shifter_files:file-details",
                      args=[file_upload.file_hex])
        response = client.get(url)

        self.assertEqual(response.status_code, 404)
