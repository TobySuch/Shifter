import hashlib
import tempfile
from shutil import rmtree

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from django_tasks_db.models import DBTaskResult

from shifter_files.models import FileUpload
from shifter_files.tasks import calculate_file_hash, schedule_file_hash

from .helpers import immediate_tasks

TEST_FILE_CONTENT = b"Hello, World!"


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CalculateFileHashTaskTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "iama@test.com", "mytemporarypassword"
        )
        self.file_upload = FileUpload.objects.create(
            owner=self.user,
            file_content=SimpleUploadedFile("hello.txt", TEST_FILE_CONTENT),
            upload_datetime=timezone.now(),
            filename="hello.txt",
        )

    def tearDown(self):
        rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def test_stores_md5_of_file(self):
        calculate_file_hash.call(self.file_upload.pk)

        self.file_upload.refresh_from_db()
        self.assertEqual(
            self.file_upload.file_hash,
            hashlib.md5(TEST_FILE_CONTENT).hexdigest(),
        )

    def test_keeps_existing_hash(self):
        FileUpload.objects.filter(pk=self.file_upload.pk).update(
            file_hash="a" * 32
        )

        calculate_file_hash.call(self.file_upload.pk)

        self.file_upload.refresh_from_db()
        self.assertEqual(self.file_upload.file_hash, "a" * 32)

    def test_ignores_deleted_file_upload(self):
        pk = self.file_upload.pk
        self.file_upload.delete()

        # Must not raise: the file was deleted before the task ran.
        calculate_file_hash.call(pk)

    def test_ignores_missing_file_content(self):
        self.file_upload.file_content.delete(save=False)

        calculate_file_hash.call(self.file_upload.pk)

        self.file_upload.refresh_from_db()
        self.assertIsNone(self.file_upload.file_hash)

    def test_schedule_enqueues_task_after_commit(self):
        with self.captureOnCommitCallbacks() as callbacks:
            schedule_file_hash(self.file_upload)
            # Nothing is queued until the transaction commits, so the
            # worker can never look for a row that isn't visible yet.
            self.assertFalse(DBTaskResult.objects.exists())

        for callback in callbacks:
            callback()

        result = DBTaskResult.objects.get()
        self.assertEqual(
            result.task_path, "shifter_files.tasks.calculate_file_hash"
        )
        self.assertEqual(
            result.args_kwargs, {"args": [self.file_upload.pk], "kwargs": {}}
        )

    @immediate_tasks
    def test_schedule_runs_task(self):
        with self.captureOnCommitCallbacks(execute=True):
            schedule_file_hash(self.file_upload)

        self.file_upload.refresh_from_db()
        self.assertEqual(
            self.file_upload.file_hash,
            hashlib.md5(TEST_FILE_CONTENT).hexdigest(),
        )
