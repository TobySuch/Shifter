import hashlib
import tempfile
from datetime import timedelta
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
    format_duration,
    get_task_log,
    get_task_stats,
    prune_task_results,
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


class PruneTaskResultsTest(TestCase):
    def test_deletes_finished_results_only(self):
        statuses = [
            TaskResultStatus.SUCCESSFUL,
            TaskResultStatus.FAILED,
            TaskResultStatus.READY,
            TaskResultStatus.RUNNING,
        ]
        for status in statuses:
            result = calculate_file_hash.enqueue(0)
            DBTaskResult.objects.filter(id=result.id).update(status=status)

        self.assertEqual(prune_task_results(), 2)
        self.assertCountEqual(
            DBTaskResult.objects.values_list("status", flat=True),
            [TaskResultStatus.READY, TaskResultStatus.RUNNING],
        )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TaskLogTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "iama@test.com", "mytemporarypassword"
        )
        self.file_upload = FileUpload.objects.create(
            owner=self.user,
            file_content=SimpleUploadedFile("report.pdf", TEST_FILE_CONTENT),
            upload_datetime=timezone.now(),
            filename="report.pdf",
        )

    def tearDown(self):
        rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def enqueue(self, file_upload_id, **fields):
        result = calculate_file_hash.enqueue(file_upload_id)
        DBTaskResult.objects.filter(id=result.id).update(**fields)
        return DBTaskResult.objects.get(id=result.id)

    def test_describes_a_finished_task(self):
        started = timezone.now() - timedelta(seconds=10)
        result = self.enqueue(
            self.file_upload.pk,
            status=TaskResultStatus.SUCCESSFUL,
            started_at=started,
            finished_at=started + timedelta(seconds=2.5),
        )

        (entry,) = get_task_log()

        self.assertEqual(entry.name, "Calculate file hash")
        self.assertEqual(entry.target, "report.pdf")
        self.assertEqual(entry.status, TaskResultStatus.SUCCESSFUL)
        self.assertEqual(entry.status_label, "Succeeded")
        self.assertEqual(entry.enqueued_at, result.enqueued_at)
        self.assertEqual(entry.duration, "2.5 s")
        self.assertEqual(entry.error, "")

    def test_describes_failed_task_with_its_exception(self):
        self.enqueue(
            self.file_upload.pk,
            status=TaskResultStatus.FAILED,
            exception_class_path="builtins.PermissionError",
        )

        (entry,) = get_task_log()

        self.assertEqual(entry.status_label, "Failed")
        self.assertEqual(entry.error, "PermissionError")

    def test_waiting_and_running_tasks_have_no_duration(self):
        self.enqueue(self.file_upload.pk)
        self.enqueue(
            self.file_upload.pk,
            status=TaskResultStatus.RUNNING,
            started_at=timezone.now(),
        )

        entries = get_task_log()

        self.assertEqual(
            [entry.status_label for entry in entries], ["Running", "Waiting"]
        )
        self.assertEqual([entry.duration for entry in entries], ["", ""])

    def test_deleted_file_is_marked(self):
        self.enqueue(12345)

        (entry,) = get_task_log()

        self.assertEqual(entry.target, "File #12345 (deleted)")

    def test_newest_first_and_limited(self):
        for _ in range(3):
            self.enqueue(self.file_upload.pk)
        newest = self.enqueue(self.file_upload.pk)

        entries = get_task_log(limit=2)

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].enqueued_at, newest.enqueued_at)

    def test_formats_longer_durations(self):
        self.assertEqual(format_duration(timedelta(seconds=0.04)), "0.0 s")
        self.assertEqual(format_duration(timedelta(seconds=59.9)), "59.9 s")
        self.assertEqual(format_duration(timedelta(seconds=75)), "1 min 15 s")
        self.assertEqual(format_duration(timedelta(hours=2)), "120 min 0 s")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TaskStatsTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "iama@test.com", "mytemporarypassword"
        )

    def tearDown(self):
        rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def make_file(self, file_hash=None):
        return FileUpload.objects.create(
            owner=self.user,
            file_content=SimpleUploadedFile("a.txt", TEST_FILE_CONTENT),
            upload_datetime=timezone.now(),
            filename="a.txt",
            file_hash=file_hash,
        )

    def add_result(self, status, finished_at=None):
        result = calculate_file_hash.enqueue(0)
        DBTaskResult.objects.filter(id=result.id).update(
            status=status, finished_at=finished_at
        )

    def test_counts_tasks_by_status_and_files_awaiting_hash(self):
        older = timezone.now() - timedelta(hours=2)
        newer = timezone.now() - timedelta(minutes=5)
        self.add_result(TaskResultStatus.READY)
        self.add_result(TaskResultStatus.READY)
        self.add_result(TaskResultStatus.RUNNING)
        self.add_result(TaskResultStatus.FAILED, finished_at=older)
        self.add_result(TaskResultStatus.SUCCESSFUL, finished_at=newer)
        self.make_file()
        self.make_file(file_hash="a" * 32)

        stats = get_task_stats()

        self.assertEqual(stats.waiting, 2)
        self.assertEqual(stats.running, 1)
        self.assertEqual(stats.failed, 1)
        self.assertEqual(stats.files_awaiting_hash, 1)
        self.assertEqual(stats.last_finished_at, newer)

    def test_empty(self):
        stats = get_task_stats()

        self.assertEqual(
            (stats.waiting, stats.running, stats.failed), (0, 0, 0)
        )
        self.assertEqual(stats.files_awaiting_hash, 0)
        self.assertIsNone(stats.last_finished_at)
