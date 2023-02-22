import datetime
import pathlib
from shutil import rmtree

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
        self.assertEqual(response.status_code, 302)

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

        self.assertEqual(response.url, reverse("shifter_files:file-details",
                                               args=[file_upload.file_hex]))

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
        self.assertEqual(response.status_code, 200)
        self.assertInHTML(("You can't upload a file with an expiry time in "
                           "the past!"), response.content.decode())
        self.assertEqual(FileUpload.objects.count(), 0)


class FileDetailsViewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(TEST_USER_EMAIL,
                                             TEST_USER_PASSWORD)

        self.user_2 = User.objects.create_user(TEST_USER_EMAIL_2,
                                               TEST_USER_PASSWORD_2)

    def tearDown(self):
        rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def test_unauthenticated_get(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        file_upload = FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() + datetime.timedelta(weeks=1),
            filename=TEST_FILE_NAME)
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
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        file_upload = FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() + datetime.timedelta(weeks=1),
            filename=TEST_FILE_NAME)
        client_2 = Client()
        client_2.login(email=TEST_USER_EMAIL_2, password=TEST_USER_PASSWORD_2)
        url = reverse("shifter_files:file-details",
                      args=[file_upload.file_hex])
        response = client_2.get(url)

        self.assertEqual(response.status_code, 404)

    def test_correct_user(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        file_upload = FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() + datetime.timedelta(weeks=1),
            filename=TEST_FILE_NAME)
        url = reverse("shifter_files:file-details",
                      args=[file_upload.file_hex])
        response = client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertInHTML(TEST_FILE_NAME, response.content.decode())
        self.assertTemplateUsed(response,
                                "shifter_files/fileupload_detail.html")

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
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        file_upload = FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() - datetime.timedelta(days=1),
            filename=TEST_FILE_NAME)
        url = reverse("shifter_files:file-details",
                      args=[file_upload.file_hex])
        response = client.get(url)

        self.assertEqual(response.status_code, 404)


class FileDownloadLandingViewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(TEST_USER_EMAIL,
                                             TEST_USER_PASSWORD)

        self.user_2 = User.objects.create_user(TEST_USER_EMAIL_2,
                                               TEST_USER_PASSWORD_2)

    def tearDown(self):
        rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def test_unauthenticated_get(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        file_upload = FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() + datetime.timedelta(weeks=1),
            filename=TEST_FILE_NAME)
        client_unauthenticated = Client()
        url = reverse("shifter_files:file-download-landing",
                      args=[file_upload.file_hex])
        response = client_unauthenticated.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response,
                                "shifter_files/file_download_landing.html")
        self.assertInHTML(f"You are downloading: {TEST_FILE_NAME}",
                          response.content.decode())

    def test_different_user(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        file_upload = FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() + datetime.timedelta(weeks=1),
            filename=TEST_FILE_NAME)
        client_2 = Client()
        client_2.login(email=TEST_USER_EMAIL_2, password=TEST_USER_PASSWORD_2)
        url = reverse("shifter_files:file-download-landing",
                      args=[file_upload.file_hex])
        response = client_2.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response,
                                "shifter_files/file_download_landing.html")
        self.assertInHTML(f"You are downloading: {TEST_FILE_NAME}",
                          response.content.decode())

    def test_file_owner_user(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        file_upload = FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() + datetime.timedelta(weeks=1),
            filename=TEST_FILE_NAME)
        url = reverse("shifter_files:file-download-landing",
                      args=[file_upload.file_hex])
        response = client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response,
                                "shifter_files/file_download_landing.html")
        self.assertInHTML(f"You are downloading: {TEST_FILE_NAME}",
                          response.content.decode())

    def test_file_does_not_exist(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse("shifter_files:file-download-landing",
                      args=['0'*32])
        response = client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_expired_file(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        file_upload = FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() - datetime.timedelta(days=1),
            filename=TEST_FILE_NAME)
        url = reverse("shifter_files:file-download-landing",
                      args=[file_upload.file_hex])
        response = client.get(url)

        self.assertEqual(response.status_code, 404)


class FileDownloadViewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(TEST_USER_EMAIL,
                                             TEST_USER_PASSWORD)

        self.user_2 = User.objects.create_user(TEST_USER_EMAIL_2,
                                               TEST_USER_PASSWORD_2)

    def tearDown(self):
        rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def test_download(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        file_upload = FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() + datetime.timedelta(weeks=1),
            filename=TEST_FILE_NAME)
        url = reverse("shifter_files:file-download",
                      args=[file_upload.file_hex])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['X-Accel-Redirect'],
                         file_upload.file_content.url)

    def test_download_anon_user(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        file_upload = FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() + datetime.timedelta(weeks=1),
            filename=TEST_FILE_NAME)
        client_anon = Client()
        url = reverse("shifter_files:file-download",
                      args=[file_upload.file_hex])
        response = client_anon.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['X-Accel-Redirect'],
                         file_upload.file_content.url)

    def test_download_another_user(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        client.login(email=TEST_USER_EMAIL_2, password=TEST_USER_PASSWORD_2)
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        file_upload = FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() + datetime.timedelta(weeks=1),
            filename=TEST_FILE_NAME)
        client_2 = Client()
        url = reverse("shifter_files:file-download",
                      args=[file_upload.file_hex])
        response = client_2.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['X-Accel-Redirect'],
                         file_upload.file_content.url)

    def test_download_does_not_exist(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() + datetime.timedelta(weeks=1),
            filename=TEST_FILE_NAME)
        url = reverse("shifter_files:file-download",
                      args=['0'*32])
        response = client.get(url)
        self.assertEqual(response.status_code, 404)


class FileDeleteViewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(TEST_USER_EMAIL,
                                             TEST_USER_PASSWORD)

        self.user_2 = User.objects.create_user(TEST_USER_EMAIL_2,
                                               TEST_USER_PASSWORD_2)

    def tearDown(self):
        rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def test_delete_does_not_exist(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() + datetime.timedelta(weeks=1),
            filename=TEST_FILE_NAME)
        url = reverse("shifter_files:file-delete",
                      args=['0'*32])
        response = client.post(url)
        self.assertEqual(response.status_code, 404)

    def test_delete_expired(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        file_upload = FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() - datetime.timedelta(weeks=1),
            filename=TEST_FILE_NAME)
        url = reverse("shifter_files:file-delete",
                      args=[file_upload.file_hex])
        response = client.post(url)
        self.assertEqual(response.status_code, 404)

    def test_delete_another_user(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        client.login(email=TEST_USER_EMAIL_2, password=TEST_USER_PASSWORD_2)
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        file_upload = FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() + datetime.timedelta(weeks=1),
            filename=TEST_FILE_NAME)
        client_2 = Client()
        url = reverse("shifter_files:file-delete",
                      args=[file_upload.file_hex])
        response = client_2.post(url)
        self.assertEqual(response.status_code, 404)

    def test_get_redirect(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        file_upload = FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() + datetime.timedelta(weeks=1),
            filename=TEST_FILE_NAME)
        url = reverse("shifter_files:file-delete",
                      args=[file_upload.file_hex])
        response = client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url,
                        reverse("shifter_files:file-details",
                                args=[file_upload.file_hex]))

    def test_delete_file(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        file_upload = FileUpload.objects.create(
            owner=self.user, file_content=test_file,
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() + datetime.timedelta(weeks=1),
            filename=TEST_FILE_NAME)
        url = reverse("shifter_files:file-delete",
                      args=[file_upload.file_hex])
        response = client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url,
                        reverse("shifter_files:myfiles"))
        file_upload.refresh_from_db()
        self.assertTrue(file_upload.is_expired())
