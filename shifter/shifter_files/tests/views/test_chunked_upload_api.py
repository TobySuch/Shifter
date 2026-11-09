import datetime
import hashlib
import json
import os
import tempfile
from shutil import rmtree
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from shifter_files.models import ChunkedUpload, FileUpload
from shifter_site_settings.models import SiteSetting

from ..helpers import immediate_tasks

TEST_USER_EMAIL = "iama@test.com"
TEST_USER_PASSWORD = "mytemporarypassword"
OTHER_USER_EMAIL = "someone@else.com"
OTHER_USER_PASSWORD = "anotherpassword1"


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(), UPLOAD_CHUNK_SIZE=8)
class ChunkedUploadApiTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            TEST_USER_EMAIL, TEST_USER_PASSWORD
        )
        self.other_user = User.objects.create_user(
            OTHER_USER_EMAIL, OTHER_USER_PASSWORD
        )
        self.client = Client()
        self.client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)

    def tearDown(self):
        rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    # Helpers

    def future_expiry(self, days=1):
        return (timezone.now() + datetime.timedelta(days=days)).isoformat()

    def init_upload(self, client=None, **overrides):
        payload = {
            "filename": "hello.txt",
            "size": 13,
            "enable_expiry": True,
            "expiry_datetime": self.future_expiry(),
            **overrides,
        }
        return (client or self.client).post(
            reverse("shifter_files:chunked-upload-init"),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def start_upload(self, **overrides):
        response = self.init_upload(**overrides)
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def send_chunk(self, session, data, offset, client=None):
        return (client or self.client).put(
            session["chunk_url"],
            data=data,
            content_type="application/octet-stream",
            headers={"X-Upload-Offset": str(offset)},
        )

    def upload_all(self, session, content):
        chunk_size = session["chunk_size"]
        for offset in range(0, len(content), chunk_size):
            response = self.send_chunk(
                session, content[offset : offset + chunk_size], offset
            )
            self.assertEqual(response.status_code, 200, response.content)

    def complete(self, session, client=None):
        return (client or self.client).post(session["complete_url"])


class ChunkedUploadInitTests(ChunkedUploadApiTestCase):
    def test_requires_authentication(self):
        response = self.init_upload(client=Client())
        self.assertEqual(response.status_code, 401)
        self.assertIn("errors", response.json())

    def test_only_post_allowed(self):
        response = self.client.get(
            reverse("shifter_files:chunked-upload-init")
        )
        self.assertEqual(response.status_code, 405)

    def test_creates_session(self):
        session = self.start_upload()

        upload = ChunkedUpload.objects.get(upload_id=session["upload_id"])
        self.assertEqual(upload.owner, self.user)
        self.assertEqual(upload.filename, "hello.txt")
        self.assertEqual(upload.total_size, 13)
        self.assertEqual(upload.received_size, 0)
        self.assertEqual(session["chunk_size"], 8)
        self.assertEqual(
            session["chunk_url"],
            reverse(
                "shifter_files:chunked-upload-chunk",
                args=[upload.upload_id],
            ),
        )
        self.assertEqual(
            session["complete_url"],
            reverse(
                "shifter_files:chunked-upload-complete",
                args=[upload.upload_id],
            ),
        )
        self.assertEqual(
            session["abort_url"],
            reverse(
                "shifter_files:chunked-upload-abort",
                args=[upload.upload_id],
            ),
        )
        self.assertTrue(os.path.exists(upload.temp_path))
        self.assertEqual(os.path.getsize(upload.temp_path), 0)

    def test_rejects_invalid_json(self):
        response = self.client.post(
            reverse("shifter_files:chunked-upload-init"),
            data="not json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response.json())

    def test_rejects_file_larger_than_max_size(self):
        SiteSetting.objects.create(name="max_file_size", value="1KB")
        response = self.init_upload(size=1025)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["errors"]["size"],
            ["You can't upload a file larger than 1KB"],
        )
        self.assertFalse(ChunkedUpload.objects.exists())

    def test_rejects_negative_size(self):
        response = self.init_upload(size=-1)
        self.assertEqual(response.status_code, 400)
        self.assertIn("size", response.json()["errors"])

    def test_rejects_expiry_in_past(self):
        response = self.init_upload(
            expiry_datetime=(
                timezone.now() - datetime.timedelta(days=1)
            ).isoformat()
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("expiry_datetime", response.json()["errors"])

    def test_rejects_expiry_too_far_in_future(self):
        response = self.init_upload(expiry_datetime=self.future_expiry(4000))
        self.assertEqual(response.status_code, 400)
        self.assertIn("expiry_datetime", response.json()["errors"])

    # #427 - a very large max expiry setting used to cause a 500 error.
    def test_accepts_far_future_expiry_with_huge_max_expiry_setting(self):
        SiteSetting.objects.create(
            name="max_expiry_offset", value="2147483647"
        )
        response = self.init_upload(
            expiry_datetime=datetime.datetime(
                5000, 1, 1, tzinfo=datetime.UTC
            ).isoformat()
        )
        self.assertEqual(response.status_code, 201, response.content)

    def test_requires_expiry_when_optional_expiry_disabled(self):
        response = self.init_upload(enable_expiry=False, expiry_datetime=None)
        self.assertEqual(response.status_code, 400)
        self.assertIn("expiry_datetime", response.json()["errors"])

    def test_allows_no_expiry_when_optional_expiry_enabled(self):
        SiteSetting.objects.create(name="allow_optional_expiry", value="True")
        session = self.start_upload(enable_expiry=False)
        upload = ChunkedUpload.objects.get(upload_id=session["upload_id"])
        self.assertIsNone(upload.expiry_datetime)

    def test_strips_path_from_filename(self):
        session = self.start_upload(filename="../../etc/passwd")
        upload = ChunkedUpload.objects.get(upload_id=session["upload_id"])
        self.assertEqual(upload.filename, "passwd")

    def test_strips_windows_path_from_filename(self):
        session = self.start_upload(filename="C:\\Users\\me\\report.pdf")
        upload = ChunkedUpload.objects.get(upload_id=session["upload_id"])
        self.assertEqual(upload.filename, "report.pdf")

    def test_rejects_empty_filename(self):
        response = self.init_upload(filename="  ")
        self.assertEqual(response.status_code, 400)
        self.assertIn("filename", response.json()["errors"])

    def test_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = self.init_upload(client=client)
        self.assertEqual(response.status_code, 403)


class ChunkedUploadChunkTests(ChunkedUploadApiTestCase):
    def test_appends_chunks_in_order(self):
        session = self.start_upload(size=13)

        first = self.send_chunk(session, b"Hello, W", 0)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json(), {"received": 8})

        second = self.send_chunk(session, b"orld!", 8)
        self.assertEqual(second.json(), {"received": 13})

        upload = ChunkedUpload.objects.get(upload_id=session["upload_id"])
        self.assertEqual(upload.received_size, 13)
        with open(upload.temp_path, "rb") as f:
            self.assertEqual(f.read(), b"Hello, World!")

    def test_rejects_wrong_offset_with_current_position(self):
        session = self.start_upload(size=13)
        self.send_chunk(session, b"Hello, W", 0)

        response = self.send_chunk(session, b"orld!", 3)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["received"], 8)

    def test_replayed_chunk_reports_conflict_without_duplicating(self):
        session = self.start_upload(size=13)
        self.send_chunk(session, b"Hello, W", 0)

        response = self.send_chunk(session, b"Hello, W", 0)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["received"], 8)
        upload = ChunkedUpload.objects.get(upload_id=session["upload_id"])
        self.assertEqual(os.path.getsize(upload.temp_path), 8)

    def test_rejects_missing_offset_header(self):
        session = self.start_upload()
        response = self.client.put(
            session["chunk_url"],
            data=b"Hello",
            content_type="application/octet-stream",
        )
        self.assertEqual(response.status_code, 400)

    def test_rejects_non_numeric_offset_header(self):
        session = self.start_upload()
        response = self.send_chunk(session, b"Hello", "abc")
        self.assertEqual(response.status_code, 400)

    def test_rejects_data_beyond_declared_size(self):
        session = self.start_upload(size=4)

        response = self.send_chunk(session, b"Hello", 0)

        self.assertEqual(response.status_code, 400)
        upload = ChunkedUpload.objects.get(upload_id=session["upload_id"])
        self.assertEqual(upload.received_size, 0)
        self.assertEqual(os.path.getsize(upload.temp_path), 0)

    def test_rejects_chunk_larger_than_chunk_size(self):
        session = self.start_upload(size=13)

        response = self.send_chunk(session, b"Hello, Wo", 0)

        self.assertEqual(response.status_code, 400)
        upload = ChunkedUpload.objects.get(upload_id=session["upload_id"])
        self.assertEqual(os.path.getsize(upload.temp_path), 0)

    def test_rejects_empty_chunk(self):
        session = self.start_upload(size=13)
        response = self.send_chunk(session, b"", 0)
        self.assertEqual(response.status_code, 400)

    def test_cannot_write_to_another_users_upload(self):
        session = self.start_upload()
        other = Client()
        other.login(email=OTHER_USER_EMAIL, password=OTHER_USER_PASSWORD)

        response = self.send_chunk(session, b"Hello", 0, client=other)

        self.assertEqual(response.status_code, 404)

    def test_requires_authentication(self):
        session = self.start_upload()
        response = self.send_chunk(session, b"Hello", 0, client=Client())
        self.assertEqual(response.status_code, 401)

    def test_unknown_upload_returns_404(self):
        response = self.send_chunk(
            {
                "chunk_url": reverse(
                    "shifter_files:chunked-upload-chunk", args=["0" * 32]
                )
            },
            b"Hello",
            0,
        )
        self.assertEqual(response.status_code, 404)


class ChunkedUploadCompleteTests(ChunkedUploadApiTestCase):
    def test_creates_file_upload(self):
        content = b"Hello, World!"
        session = self.start_upload(size=len(content))
        self.upload_all(session, content)
        upload = ChunkedUpload.objects.get(upload_id=session["upload_id"])
        temp_path = upload.temp_path

        response = self.complete(session)

        self.assertEqual(response.status_code, 201, response.content)
        file_upload = FileUpload.objects.get()
        self.assertEqual(
            response.json(),
            {
                "redirect_url": reverse(
                    "shifter_files:file-details", args=[file_upload.file_hex]
                )
            },
        )
        self.assertEqual(file_upload.owner, self.user)
        self.assertEqual(file_upload.filename, "hello.txt")
        self.assertEqual(file_upload.expiry_datetime, upload.expiry_datetime)
        # Hashing happens in a background task after the response.
        self.assertIsNone(file_upload.file_hash)
        self.assertTrue(
            file_upload.file_content.name.startswith(
                f"uploads/hello.txt_{file_upload.file_hex}"
            )
        )
        with file_upload.file_content.open("rb") as f:
            self.assertEqual(f.read(), content)
        self.assertFalse(ChunkedUpload.objects.exists())
        self.assertFalse(os.path.exists(temp_path))

    @immediate_tasks
    def test_hash_is_calculated_by_background_task(self):
        content = b"0123456789abcdef!"
        session = self.start_upload(size=len(content))
        self.upload_all(session, content)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.complete(session)

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(
            FileUpload.objects.get().file_hash,
            hashlib.md5(content).hexdigest(),
        )

    def test_completed_file_is_downloadable(self):
        content = b"0123456789abcdef!"
        session = self.start_upload(size=len(content))
        self.upload_all(session, content)
        self.complete(session)
        file_upload = FileUpload.objects.get()

        response = Client().get(
            reverse("shifter_files:file-download", args=[file_upload.file_hex])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), content)

    @immediate_tasks
    def test_empty_file(self):
        session = self.start_upload(size=0)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.complete(session)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            FileUpload.objects.get().file_hash, hashlib.md5(b"").hexdigest()
        )

    def test_failed_save_keeps_upload_resumable(self):
        content = b"Hello, World!"
        session = self.start_upload(size=len(content))
        self.upload_all(session, content)
        temp_path = ChunkedUpload.objects.get().temp_path

        with (
            mock.patch.object(
                FileUpload, "save", side_effect=RuntimeError("db down")
            ),
            self.assertRaises(RuntimeError),
        ):
            self.complete(session)

        # The temp file is back in place and nothing was left in storage,
        # so completing again succeeds.
        self.assertTrue(os.path.exists(temp_path))
        self.assertEqual(
            os.listdir(os.path.join(settings.MEDIA_ROOT, "uploads")), []
        )
        response = self.complete(session)
        self.assertEqual(response.status_code, 201)

    def test_rejects_incomplete_upload(self):
        session = self.start_upload(size=13)
        self.send_chunk(session, b"Hello, W", 0)

        response = self.complete(session)

        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response.json())
        self.assertFalse(FileUpload.objects.exists())
        self.assertTrue(ChunkedUpload.objects.exists())

    def test_cannot_complete_another_users_upload(self):
        session = self.start_upload(size=0)
        other = Client()
        other.login(email=OTHER_USER_EMAIL, password=OTHER_USER_PASSWORD)

        response = self.complete(session, client=other)

        self.assertEqual(response.status_code, 404)
        self.assertFalse(FileUpload.objects.exists())

    def test_cannot_complete_twice(self):
        session = self.start_upload(size=0)
        self.complete(session)

        response = self.complete(session)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(FileUpload.objects.count(), 1)


class ChunkedUploadAbortTests(ChunkedUploadApiTestCase):
    def test_abort_removes_session_and_temp_file(self):
        session = self.start_upload(size=13)
        self.send_chunk(session, b"Hello, W", 0)
        temp_path = ChunkedUpload.objects.get().temp_path

        response = self.client.delete(session["abort_url"])

        self.assertEqual(response.status_code, 204)
        self.assertFalse(ChunkedUpload.objects.exists())
        self.assertFalse(os.path.exists(temp_path))

    def test_cannot_abort_another_users_upload(self):
        session = self.start_upload()
        other = Client()
        other.login(email=OTHER_USER_EMAIL, password=OTHER_USER_PASSWORD)

        response = other.delete(session["abort_url"])

        self.assertEqual(response.status_code, 404)
        self.assertTrue(ChunkedUpload.objects.exists())
