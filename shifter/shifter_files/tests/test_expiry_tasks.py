import tempfile
from datetime import timedelta
from io import StringIO
from shutil import rmtree

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.tasks import TaskResultStatus
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django_tasks_db.models import DBTaskResult

from shifter_files.models import FileUpload
from shifter_files.tasks import (
    delete_expired_file,
    get_task_log,
    get_task_stats,
    requeue_missing_expiry_tasks,
)

from .helpers import immediate_tasks

PASSWORD = "mytemporarypassword"


def scheduled_deletions():
    """(file id, run_after) for every waiting delete task."""
    return sorted(
        (result.args_kwargs["args"][0], result.run_after)
        for result in DBTaskResult.objects.filter(
            task_path=delete_expired_file.module_path,
            status=TaskResultStatus.READY,
        )
    )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ExpiryTaskTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "iama@test.com", PASSWORD
        )

    def tearDown(self):
        rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def make_file(self, expiry_datetime):
        with self.captureOnCommitCallbacks(execute=True):
            return FileUpload.objects.create(
                owner=self.user,
                file_content=SimpleUploadedFile("a.txt", b"hello"),
                upload_datetime=timezone.now(),
                expiry_datetime=expiry_datetime,
                filename="a.txt",
            )

    def save(self, file_upload):
        with self.captureOnCommitCallbacks(execute=True):
            file_upload.save()


class DeleteExpiredFileTaskTest(ExpiryTaskTestCase):
    def test_deletes_expired_file_and_its_content(self):
        file_upload = self.make_file(timezone.now() - timedelta(minutes=1))
        path = file_upload.file_content.path

        delete_expired_file.call(file_upload.pk)

        self.assertFalse(FileUpload.objects.exists())
        self.assertFalse(
            FileUpload.file_content.field.storage.exists(path),
        )

    def test_keeps_file_whose_expiry_moved_later(self):
        file_upload = self.make_file(timezone.now() + timedelta(days=1))

        delete_expired_file.call(file_upload.pk)

        self.assertTrue(FileUpload.objects.filter(pk=file_upload.pk).exists())

    def test_keeps_file_without_expiry(self):
        file_upload = self.make_file(None)

        delete_expired_file.call(file_upload.pk)

        self.assertTrue(FileUpload.objects.filter(pk=file_upload.pk).exists())

    def test_ignores_file_already_deleted(self):
        delete_expired_file.call(12345)


class ScheduleFileExpiryTest(ExpiryTaskTestCase):
    def test_new_file_schedules_deletion_at_expiry(self):
        expiry = timezone.now() + timedelta(days=1)

        file_upload = self.make_file(expiry)

        self.assertEqual(scheduled_deletions(), [(file_upload.pk, expiry)])

    def test_file_without_expiry_schedules_nothing(self):
        self.make_file(None)

        self.assertEqual(scheduled_deletions(), [])

    def test_saving_again_does_not_duplicate(self):
        expiry = timezone.now() + timedelta(days=1)
        file_upload = self.make_file(expiry)

        file_upload.filename = "renamed.txt"
        self.save(file_upload)

        self.assertEqual(scheduled_deletions(), [(file_upload.pk, expiry)])

    def test_changing_expiry_replaces_the_scheduled_deletion(self):
        file_upload = self.make_file(timezone.now() + timedelta(days=1))
        new_expiry = timezone.now() + timedelta(days=7)

        file_upload.expiry_datetime = new_expiry
        self.save(file_upload)

        self.assertEqual(
            scheduled_deletions(), [(file_upload.pk, new_expiry)]
        )

    def test_clearing_expiry_cancels_the_scheduled_deletion(self):
        file_upload = self.make_file(timezone.now() + timedelta(days=1))

        file_upload.expiry_datetime = None
        self.save(file_upload)

        self.assertEqual(scheduled_deletions(), [])

    def test_deleting_file_cancels_its_scheduled_deletion(self):
        file_upload = self.make_file(timezone.now() + timedelta(days=1))

        file_upload.delete()

        self.assertEqual(scheduled_deletions(), [])

    def test_other_files_keep_their_scheduled_deletions(self):
        expiry = timezone.now() + timedelta(days=1)
        keep = self.make_file(expiry)
        change = self.make_file(expiry)

        change.expiry_datetime = None
        self.save(change)

        self.assertEqual(scheduled_deletions(), [(keep.pk, expiry)])

    @immediate_tasks
    def test_backend_without_scheduling_skips_future_deletions(self):
        # The immediate backend can't defer tasks, so only deletions that
        # are already due are run; future ones are left to the startup
        # check and the manual cleanup.
        future = self.make_file(timezone.now() + timedelta(days=1))
        self.make_file(timezone.now() - timedelta(minutes=1))

        self.assertEqual(list(FileUpload.objects.all()), [future])

    @immediate_tasks
    def test_delete_button_removes_the_file(self):
        file_upload = self.make_file(timezone.now() + timedelta(days=1))
        client = Client()
        client.login(email=self.user.email, password=PASSWORD)

        with self.captureOnCommitCallbacks(execute=True):
            response = client.post(
                reverse(
                    "shifter_files:file-delete", args=[file_upload.file_hex]
                )
            )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(FileUpload.objects.exists())


class RequeueMissingExpiryTasksTest(ExpiryTaskTestCase):
    def test_queues_files_missing_a_deletion(self):
        expiry = timezone.now() + timedelta(days=1)
        file_upload = self.make_file(expiry)
        DBTaskResult.objects.all().delete()

        self.assertEqual(requeue_missing_expiry_tasks(), 1)
        self.assertEqual(scheduled_deletions(), [(file_upload.pk, expiry)])

    def test_skips_files_already_scheduled_and_without_expiry(self):
        self.make_file(timezone.now() + timedelta(days=1))
        self.make_file(None)

        self.assertEqual(requeue_missing_expiry_tasks(), 0)
        self.assertEqual(len(scheduled_deletions()), 1)

    def test_queues_already_expired_files(self):
        # e.g. files that expired while the old cron job was in charge.
        expired = timezone.now() - timedelta(hours=1)
        file_upload = self.make_file(expired)
        DBTaskResult.objects.all().delete()

        self.assertEqual(requeue_missing_expiry_tasks(), 1)
        self.assertEqual(scheduled_deletions(), [(file_upload.pk, expired)])

    def test_command_reports_queued_expiry_tasks(self):
        self.make_file(timezone.now() + timedelta(days=1))
        DBTaskResult.objects.all().delete()
        out = StringIO()

        call_command("rescheduletasks", "--no-color", stdout=out)

        self.assertIn("Queued 1 file expiry task(s).", out.getvalue())


class ScheduledTaskDisplayTest(ExpiryTaskTestCase):
    def test_log_marks_future_tasks_as_scheduled(self):
        expiry = timezone.now() + timedelta(days=1)
        self.make_file(expiry)

        (entry,) = get_task_log()

        self.assertEqual(entry.name, "Delete expired file")
        self.assertEqual(entry.target, "a.txt")
        self.assertEqual(entry.status_label, "Scheduled")
        self.assertEqual(entry.run_after, expiry)

    def test_stats_count_scheduled_separately_from_waiting(self):
        self.make_file(timezone.now() + timedelta(days=1))
        self.make_file(timezone.now() + timedelta(days=2))
        self.make_file(timezone.now() - timedelta(minutes=1))

        stats = get_task_stats()

        self.assertEqual(stats.scheduled, 2)
        self.assertEqual(stats.waiting, 1)
