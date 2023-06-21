from django.core.management.base import BaseCommand
from shifter_files.models import FileUpload


class Command(BaseCommand):
    help = 'Deletes all expired files'

    def handle(self, *args, **kwargs):
        num_files_deleted = FileUpload.delete_expired_files()
        if num_files_deleted > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted {num_files_deleted} '
                    'expired file(s)')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('No expired files to be deleted')
            )
