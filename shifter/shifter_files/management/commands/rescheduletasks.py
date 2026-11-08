from django.core.management.base import BaseCommand

from shifter_files.tasks import requeue_missing_hashes


class Command(BaseCommand):
    help = (
        "Queue background tasks that may have been lost, e.g. while the "
        "task worker was stopped. Run on startup by entrypoint.sh."
    )

    def handle(self, *args, **options):
        count = requeue_missing_hashes()
        self.stdout.write(
            self.style.SUCCESS(f"Queued {count} file hash task(s).")
        )
