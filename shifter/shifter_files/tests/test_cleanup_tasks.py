import pathlib
import tempfile
from datetime import timedelta
from io import StringIO
from shutil import rmtree

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.tasks import TaskResultStatus
from django.test import TestCase, override_settings
from django.utils import timezone
from django_tasks_db.models import DBTaskResult

from shifter_files.models import ChunkedUpload
from shifter_files.tasks import (
    delete_stale_chunked_upload,
    ensure_prune_scheduled,
    prune_old_task_results,
    requeue_missing_chunked_upload_cleanup,
)
from shifter_site_settings.models import SiteSetting


def waiting(task):
    """(args, run_after) for every waiting run of ``task``."""
    return sorted(
        (tuple(result.args_kwargs["args"]), result.run_after)
        for result in DBTaskResult.objects.filter(
            task_path=task.module_path, status=TaskResultStatus.READY
        )
    )


@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(), CHUNKED_UPLOAD_MAX_AGE_HOURS=24
)
class StaleChunkedUploadTaskTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "iama@test.com", "mytemporarypassword"
        )

    def tearDown(self):
        rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def make_upload(self):
        with self.captureOnCommitCallbacks(execute=True):
            upload = ChunkedUpload.objects.create(
                owner=self.user, filename="partial.bin", total_size=10
            )
        upload.create_temp_file()
        return upload

    def backdate(self, upload, hours):
        # updated_at is auto_now, so backdate it with a queryset update.
        updated_at = timezone.now() - timedelta(hours=hours)
        ChunkedUpload.objects.filter(pk=upload.pk).update(
            updated_at=updated_at
        )
        return updated_at

    def test_new_upload_schedules_a_check_when_it_would_go_stale(self):
        upload = self.make_upload()

        ((args, run_after),) = waiting(delete_stale_chunked_upload)

        self.assertEqual(args, (upload.pk,))
        self.assertEqual(run_after, upload.updated_at + timedelta(hours=24))

    def test_deletes_upload_untouched_for_max_age(self):
        upload = self.make_upload()
        self.backdate(upload, hours=25)

        delete_stale_chunked_upload.call(upload.pk)

        self.assertFalse(ChunkedUpload.objects.exists())
        self.assertFalse(pathlib.Path(upload.temp_path).exists())

    def test_active_upload_is_checked_again_later(self):
        upload = self.make_upload()
        updated_at = self.backdate(upload, hours=2)
        DBTaskResult.objects.all().delete()

        delete_stale_chunked_upload.call(upload.pk)

        self.assertTrue(ChunkedUpload.objects.exists())
        self.assertEqual(
            waiting(delete_stale_chunked_upload),
            [((upload.pk,), updated_at + timedelta(hours=24))],
        )

    def test_finished_upload_cancels_its_check(self):
        upload = self.make_upload()

        upload.delete()

        self.assertEqual(waiting(delete_stale_chunked_upload), [])

    def test_ignores_upload_already_gone(self):
        delete_stale_chunked_upload.call(12345)

    def test_startup_requeues_missing_checks(self):
        upload = self.make_upload()
        updated_at = self.backdate(upload, hours=30)
        DBTaskResult.objects.all().delete()
        self.make_upload()  # already has its check

        self.assertEqual(requeue_missing_chunked_upload_cleanup(), 1)
        self.assertIn(
            ((upload.pk,), updated_at + timedelta(hours=24)),
            waiting(delete_stale_chunked_upload),
        )


class PruneOldTaskResultsTest(TestCase):
    def set_retention(self, days):
        SiteSetting.objects.update_or_create(
            name="task_history_retention_days", defaults={"value": str(days)}
        )

    def add_result(self, status, finished_days_ago=None, started_hours_ago=0):
        result = delete_stale_chunked_upload.enqueue(0)
        now = timezone.now()
        DBTaskResult.objects.filter(id=result.id).update(
            status=status,
            started_at=now - timedelta(hours=started_hours_ago),
            finished_at=(
                now - timedelta(days=finished_days_ago)
                if finished_days_ago is not None
                else None
            ),
        )
        return str(result.id)

    def remaining(self):
        return {
            str(pk) for pk in DBTaskResult.objects.values_list("id", flat=True)
        }

    def test_deletes_old_finished_and_stuck_running_results(self):
        self.set_retention(7)
        old_success = self.add_result(TaskResultStatus.SUCCESSFUL, 8)
        old_failure = self.add_result(TaskResultStatus.FAILED, 8)
        recent = self.add_result(TaskResultStatus.SUCCESSFUL, 1)
        stuck = self.add_result(
            TaskResultStatus.RUNNING, started_hours_ago=25
        )
        running = self.add_result(
            TaskResultStatus.RUNNING, started_hours_ago=1
        )

        prune_old_task_results.call()

        remaining = self.remaining()
        self.assertTrue({recent, running} <= remaining)
        self.assertFalse({old_success, old_failure, stuck} & remaining)

    def test_keeps_everything_by_default(self):
        old_success = self.add_result(TaskResultStatus.SUCCESSFUL, 400)
        stuck = self.add_result(
            TaskResultStatus.RUNNING, started_hours_ago=25
        )

        prune_old_task_results.call()

        self.assertTrue({old_success, stuck} <= self.remaining())

    def test_keeps_everything_when_retention_is_zero(self):
        self.set_retention(0)
        old_failure = self.add_result(TaskResultStatus.FAILED, 400)

        prune_old_task_results.call()

        self.assertIn(old_failure, self.remaining())

    def test_schedules_its_next_run_a_day_later(self):
        before = timezone.now()

        prune_old_task_results.call()

        ((args, run_after),) = waiting(prune_old_task_results)
        self.assertEqual(args, ())
        self.assertGreaterEqual(run_after, before + timedelta(days=1))
        self.assertLess(run_after, before + timedelta(days=1, minutes=1))

    def test_startup_schedules_prune_once(self):
        self.assertTrue(ensure_prune_scheduled())
        self.assertFalse(ensure_prune_scheduled())

        self.assertEqual(len(waiting(prune_old_task_results)), 1)


class RescheduleTasksCommandTest(TestCase):
    def test_reports_cleanup_and_prune(self):
        out = StringIO()

        call_command("rescheduletasks", "--no-color", stdout=out)

        output = out.getvalue()
        self.assertIn("Queued 0 chunked upload cleanup task(s).", output)
        self.assertIn("Scheduled task history pruning.", output)
