from django.core.management.base import BaseCommand
from django.db.models.functions import Now
from shifter_files.models import FileUpload


class Command(BaseCommand):
    help = 'Deletes all expired files'

    def handle(self, *args, **kwargs):
        expired_files = FileUpload.objects.filter(expiry_datetime__lte=Now())
        if expired_files:
            FileUpload.objects.filter(expiry_datetime__lte=Now()).delete()
            # success message
            self.stdout.write(
                self.style.SUCCESS('Successfully deleted all expired files')
            )
        else:
            # no expired files message
            self.stdout.write(
                self.style.ERROR('No expired files to be deleted')
            )
