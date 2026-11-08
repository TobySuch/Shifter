from dataclasses import dataclass
from datetime import datetime

from django.db import transaction
from django.tasks import TaskResultStatus, task
from django_tasks_db.models import DBTaskResult

from .models import FileUpload


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


def prune_task_results():
    """Delete the records of finished (successful or failed) tasks."""
    deleted, _ = DBTaskResult.objects.finished().delete()
    return deleted


TASK_LOG_LIMIT = 50

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


def format_duration(duration):
    seconds = duration.total_seconds()
    if seconds < 60:
        return f"{seconds:.1f} s"
    minutes, seconds = divmod(round(seconds), 60)
    return f"{minutes} min {seconds} s"


def _task_name(task_path):
    """calculate_file_hash -> "Calculate file hash"."""
    return task_path.rsplit(".", 1)[-1].replace("_", " ").capitalize()


def _hash_targets(results):
    """File names for the hash tasks in ``results``, keyed by FileUpload pk."""
    ids = {
        result.args_kwargs["args"][0]
        for result in results
        if result.task_path == calculate_file_hash.module_path
    }
    return dict(
        FileUpload.objects.filter(pk__in=ids).values_list("pk", "filename")
    )


def _target(result, hash_targets):
    args = result.args_kwargs.get("args", [])
    if result.task_path == calculate_file_hash.module_path:
        pk = args[0]
        return hash_targets.get(pk, f"File #{pk} (deleted)")
    return ", ".join(str(arg) for arg in args)


def get_task_log(limit=TASK_LOG_LIMIT):
    """The most recently queued background tasks, newest first."""
    results = list(DBTaskResult.objects.order_by("-enqueued_at")[:limit])
    hash_targets = _hash_targets(results)
    entries = []
    for result in results:
        duration = ""
        if result.started_at and result.finished_at:
            duration = format_duration(result.finished_at - result.started_at)
        error = ""
        if result.status == TaskResultStatus.FAILED:
            error = result.exception_class_path.rsplit(".", 1)[-1]
        entries.append(
            TaskLogEntry(
                name=_task_name(result.task_path),
                target=_target(result, hash_targets),
                status=result.status,
                status_label=STATUS_LABELS.get(result.status, result.status),
                enqueued_at=result.enqueued_at,
                started_at=result.started_at,
                finished_at=result.finished_at,
                duration=duration,
                error=error,
            )
        )
    return entries


def count_tasks():
    return DBTaskResult.objects.count()
