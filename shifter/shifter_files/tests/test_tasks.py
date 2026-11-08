import hashlib
import tempfile
from io import StringIO
from shutil import rmtree

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.tasks import TaskResultStatus
from django.test import TestCase, override_settings
from django.utils import timezone
from django_tasks_db.models import DBTaskResult

from shifter_files.models import FileUpload
from shifter_files.tasks import (
    calculate_file_hash,
    requeue_missing_hashes,
    schedule_file_hash,
)

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


def queued_hash_ids():
    return [
        result.args_kwargs["args"][0]
        for result in DBTaskResult.objects.filter(
            task_path="shifter_files.tasks.calculate_file_hash",
            status=TaskResultStatus.READY,
        )
    ]


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class RequeueMissingHashesTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "iama@test.com", "mytemporarypassword"
        )

    def tearDown(self):
        rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def make_file(self, file_hash=None):
        return FileUpload.objects.create(
            owner=self.user,
            file_content=SimpleUploadedFile("hello.txt", TEST_FILE_CONTENT),
            upload_datetime=timezone.now(),
            filename="hello.txt",
            file_hash=file_hash,
        )

    def test_queues_files_without_a_hash(self):
        missing = self.make_file()
        self.make_file(file_hash="a" * 32)

        self.assertEqual(requeue_missing_hashes(), 1)
        self.assertEqual(queued_hash_ids(), [missing.pk])

    def test_skips_files_already_queued(self):
        file_upload = self.make_file()
        calculate_file_hash.enqueue(file_upload.pk)

        self.assertEqual(requeue_missing_hashes(), 0)
        self.assertEqual(queued_hash_ids(), [file_upload.pk])

    def test_requeues_task_lost_while_running(self):
        # A worker killed mid-task leaves its result marked RUNNING forever.
        file_upload = self.make_file()
        calculate_file_hash.enqueue(file_upload.pk)
        DBTaskResult.objects.update(status=TaskResultStatus.RUNNING)

        self.assertEqual(requeue_missing_hashes(), 1)
        self.assertEqual(queued_hash_ids(), [file_upload.pk])

    def test_command_reports_queued_tasks(self):
        self.make_file()
        out = StringIO()

        call_command("rescheduletasks", "--no-color", stdout=out)

        self.assertIn("Queued 1 file hash task(s).", out.getvalue())
        self.assertEqual(len(queued_hash_ids()), 1)

