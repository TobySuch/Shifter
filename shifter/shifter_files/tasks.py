from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Case, Count, F, Max, Q, When
from django.tasks import TaskResultStatus, task
from django.utils import timezone
from django_tasks_db.models import DBTaskResult, get_date_max

from .models import ChunkedUpload, FileUpload


@task
def calculate_file_hash(file_upload_id):
    """Store the MD5 of an uploaded file.

    Runs in the task worker so large uploads don't wait for the whole file
    to be read again before the request returns.
    """
    file_upload = FileUpload.objects.filter(
        pk=file_upload_id, file_hash__isnull=True
    ).first()
    if file_upload is None:
        # Deleted before the task ran, or already hashed.
        return

    try:
        with file_upload.file_content.open("rb") as f:
            file_hash = FileUpload.calculate_file_hash(f)
    except FileNotFoundError:
        return

    FileUpload.objects.filter(pk=file_upload_id).update(file_hash=file_hash)


def schedule_file_hash(file_upload):
    """Queue the hash once the transaction that created the file commits."""
    pk = file_upload.pk
    transaction.on_commit(lambda: calculate_file_hash.enqueue(pk))


def requeue_missing_hashes():
    """Queue a hash task for every file that still has no hash.

    Covers tasks that were lost (e.g. the container stopped while the
    worker was running one, leaving it marked RUNNING forever) and files
    uploaded before hashes were calculated. Files with a task already
    waiting are skipped. Returns how many tasks were queued.
    """
    already_queued = {
        args_kwargs["args"][0]
        for args_kwargs in DBTaskResult.objects.filter(
            task_path=calculate_file_hash.module_path,
            status=TaskResultStatus.READY,
        ).values_list("args_kwargs", flat=True)
    }
    missing = FileUpload.objects.filter(file_hash__isnull=True).exclude(
        pk__in=already_queued
    )
    count = 0
    for pk in missing.values_list("pk", flat=True):
        calculate_file_hash.enqueue(pk)
        count += 1
    return count


@task
def delete_expired_file(file_upload_id):
    """Delete a file once it has expired.

    Queued to run at the file's expiry time. The expiry is checked again
    here so a deletion left over from an earlier expiry does nothing.
    """
    file_upload = FileUpload.objects.filter(pk=file_upload_id).first()
    if file_upload is None or not file_upload.is_expired():
        return
    # The pre_delete signal removes the file from storage.
    file_upload.delete()


def _waiting_deletions(file_upload_id):
    return DBTaskResult.objects.filter(
        task_path=delete_expired_file.module_path,
        status=TaskResultStatus.READY,
        args_kwargs__args__0=file_upload_id,
    )


def cancel_file_expiry(file_upload_id):
    """Drop any deletion still waiting for this file."""
    _waiting_deletions(file_upload_id).delete()


def _enqueue_at(task_obj, run_after, *args):
    """Queue ``task_obj`` to run at ``run_after``."""
    if not task_obj.get_backend().supports_defer:
        # Backends that can't defer (e.g. the immediate backend used in
        # tests) only run tasks that are already due.
        if run_after <= timezone.now():
            task_obj.enqueue(*args)
        return
    task_obj.using(run_after=run_after).enqueue(*args)


def _ensure_deletion(file_upload_id, run_after):
    """Make the file's only waiting deletion the one at ``run_after``."""
    waiting = _waiting_deletions(file_upload_id)
    if run_after is None:
        waiting.delete()
        return
    waiting.exclude(run_after=run_after).delete()
    if not waiting.filter(run_after=run_after).exists():
        _enqueue_at(delete_expired_file, run_after, file_upload_id)


def schedule_file_expiry(file_upload):
    """Schedule (or cancel) the file's deletion to match its expiry.

    Called whenever a FileUpload is saved; runs after the transaction
    commits so the worker sees the saved expiry.
    """
    pk, run_after = file_upload.pk, file_upload.expiry_datetime
    transaction.on_commit(lambda: _ensure_deletion(pk, run_after))


def requeue_missing_expiry_tasks():
    """Schedule a deletion for every file with an expiry but no deletion.

    Files that have already expired get a deletion that runs straight
    away. Returns how many tasks were queued.
    """
    scheduled = {
        (args_kwargs["args"][0], run_after)
        for args_kwargs, run_after in DBTaskResult.objects.filter(
            task_path=delete_expired_file.module_path,
            status=TaskResultStatus.READY,
        ).values_list("args_kwargs", "run_after")
    }
    count = 0
    files = FileUpload.objects.filter(expiry_datetime__isnull=False)
    for pk, expiry in files.values_list("pk", "expiry_datetime"):
        if (pk, expiry) not in scheduled:
            _enqueue_at(delete_expired_file, expiry, pk)
            count += 1
    return count


def _stale_after(chunked_upload):
    return chunked_upload.updated_at + timedelta(
        hours=settings.CHUNKED_UPLOAD_MAX_AGE_HOURS
    )


@task
def delete_stale_chunked_upload(chunked_upload_id):
    """Delete an unfinished upload nobody has added to for a while.

    Scheduled for when a new upload would go stale. If chunks have
    arrived since, the check is scheduled again for the new deadline.
    """
    upload = ChunkedUpload.objects.filter(pk=chunked_upload_id).first()
    if upload is None:
        return
    stale_after = _stale_after(upload)
    if stale_after > timezone.now():
        _enqueue_at(delete_stale_chunked_upload, stale_after, upload.pk)
        return
    # The pre_delete signal removes the temp file.
    upload.delete()


def _waiting_chunked_upload_checks(chunked_upload_id):
    return DBTaskResult.objects.filter(
        task_path=delete_stale_chunked_upload.module_path,
        status=TaskResultStatus.READY,
        args_kwargs__args__0=chunked_upload_id,
    )


def schedule_chunked_upload_cleanup(chunked_upload):
    pk, stale_after = chunked_upload.pk, _stale_after(chunked_upload)
    transaction.on_commit(
        lambda: _enqueue_at(delete_stale_chunked_upload, stale_after, pk)
    )


def cancel_chunked_upload_cleanup(chunked_upload_id):
    _waiting_chunked_upload_checks(chunked_upload_id).delete()


def requeue_missing_chunked_upload_cleanup():
    """Schedule a stale check for every unfinished upload without one."""
    checked = {
        args_kwargs["args"][0]
        for args_kwargs in DBTaskResult.objects.filter(
            task_path=delete_stale_chunked_upload.module_path,
            status=TaskResultStatus.READY,
        ).values_list("args_kwargs", flat=True)
    }
    count = 0
    for upload in ChunkedUpload.objects.exclude(pk__in=checked):
        _enqueue_at(
            delete_stale_chunked_upload, _stale_after(upload), upload.pk
        )
        count += 1
    return count


# A task left RUNNING this long was interrupted (e.g. the container
# stopped) and will never finish.
STUCK_TASK_AGE = timedelta(days=1)
PRUNE_INTERVAL = timedelta(days=1)


@task
def prune_old_task_results():
    """Delete old task records, then run again tomorrow.

    Removes finished tasks older than TASK_RESULT_MAX_AGE_DAYS and tasks
    stuck as RUNNING for over a day. The next run is queued first so a
    failure here doesn't stop pruning.
    """
    now = timezone.now()
    _enqueue_at(prune_old_task_results, now + PRUNE_INTERVAL)
    DBTaskResult.objects.finished().filter(
        finished_at__lt=now - timedelta(days=settings.TASK_RESULT_MAX_AGE_DAYS)
    ).delete()
    DBTaskResult.objects.running().filter(
        started_at__lt=now - STUCK_TASK_AGE
    ).delete()


def ensure_prune_scheduled():
    """Queue the pruning task unless a run is already waiting.

    Returns True if it was queued.
    """
    already = DBTaskResult.objects.filter(
        task_path=prune_old_task_results.module_path,
        status=TaskResultStatus.READY,
    ).exists()
    if already:
        return False
    prune_old_task_results.enqueue()
    return True


def prune_task_results():
    """Delete the records of finished (successful or failed) tasks."""
    deleted, _ = DBTaskResult.objects.finished().delete()
    return deleted


TASK_LOG_LIMIT = 50

SCHEDULED_LABEL = "Scheduled"
STATUS_LABELS = {
    TaskResultStatus.READY: "Waiting",
    TaskResultStatus.RUNNING: "Running",
    TaskResultStatus.SUCCESSFUL: "Succeeded",
    TaskResultStatus.FAILED: "Failed",
}


@dataclass(frozen=True)
class TaskLogEntry:
    name: str
    target: str
    status: str
    status_label: str
    enqueued_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    duration: str
    error: str
    # Set for waiting tasks that are scheduled to run in the future.
    run_after: datetime | None = None


def format_duration(duration):
    seconds = duration.total_seconds()
    if seconds < 60:
        return f"{seconds:.1f} s"
    minutes, seconds = divmod(round(seconds), 60)
    return f"{minutes} min {seconds} s"


def _task_name(task_path):
    """calculate_file_hash -> "Calculate file hash"."""
    return task_path.rsplit(".", 1)[-1].replace("_", " ").capitalize()


def _file_task_paths():
    return {calculate_file_hash.module_path, delete_expired_file.module_path}


def _file_targets(results):
    """File names for the file tasks in ``results``, keyed by FileUpload pk."""
    file_tasks = _file_task_paths()
    ids = {
        result.args_kwargs["args"][0]
        for result in results
        if result.task_path in file_tasks
    }
    return dict(
        FileUpload.objects.filter(pk__in=ids).values_list("pk", "filename")
    )


def _target(result, file_targets):
    args = result.args_kwargs.get("args", [])
    if result.task_path in _file_task_paths():
        pk = args[0]
        return file_targets.get(pk, f"File #{pk} (deleted)")
    return ", ".join(str(arg) for arg in args)


def _is_scheduled(result, now):
    return (
        result.status == TaskResultStatus.READY
        and now < result.run_after != get_date_max()
    )


def get_task_log(limit=TASK_LOG_LIMIT):
    """Background tasks, latest scheduled time first.

    A task's scheduled time is when it was set to run, or when it was
    queued if it was set to run straight away, so tasks scheduled for the
    future come first.
    """
    scheduled_for = Case(
        When(run_after=get_date_max(), then=F("enqueued_at")),
        default=F("run_after"),
    )
    results = list(
        DBTaskResult.objects.order_by(
            scheduled_for.desc(), "-enqueued_at"
        )[:limit]
    )
    file_targets = _file_targets(results)
    now = timezone.now()
    entries = []
    for result in results:
        scheduled = _is_scheduled(result, now)
        duration = ""
        if result.started_at and result.finished_at:
            duration = format_duration(result.finished_at - result.started_at)
        error = ""
        if result.status == TaskResultStatus.FAILED:
            error = result.exception_class_path.rsplit(".", 1)[-1]
        entries.append(
            TaskLogEntry(
                name=_task_name(result.task_path),
                target=_target(result, file_targets),
                status=result.status,
                status_label=(
                    SCHEDULED_LABEL
                    if scheduled
                    else STATUS_LABELS.get(result.status, result.status)
                ),
                enqueued_at=result.enqueued_at,
                started_at=result.started_at,
                finished_at=result.finished_at,
                duration=duration,
                error=error,
                run_after=result.run_after if scheduled else None,
            )
        )
    return entries


def count_tasks():
    return DBTaskResult.objects.count()


@dataclass(frozen=True)
class TaskStats:
    # Due now (or queued without a time) and waiting for the worker.
    waiting: int
    # Waiting until a time in the future, e.g. deletions at file expiry.
    scheduled: int
    running: int
    failed: int
    last_finished_at: datetime | None


def get_task_stats():
    """Counts for the Site Information panel."""
    now = timezone.now()
    ready = Q(status=TaskResultStatus.READY)
    due = Q(run_after__lte=now) | Q(run_after=get_date_max())
    totals = DBTaskResult.objects.aggregate(
        waiting=Count("id", filter=ready & due),
        scheduled=Count("id", filter=ready & ~due),
        running=Count("id", filter=Q(status=TaskResultStatus.RUNNING)),
        failed=Count("id", filter=Q(status=TaskResultStatus.FAILED)),
        last_finished_at=Max("finished_at"),
    )
    return TaskStats(**totals)
