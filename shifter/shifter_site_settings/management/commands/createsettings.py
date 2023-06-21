from django.core.management.base import BaseCommand
from django.conf import settings
from shifter_site_settings.models import SiteSetting


class Command(BaseCommand):
    help = 'Sets up the initial site settings in the database.'

    def handle(self, *args, **kwargs):
        for setting_key in settings.SITE_SETTINGS.keys():
            # Check if setting_key already exists
            if not SiteSetting.objects.filter(name=setting_key).exists():
                # Create setting_key
                SiteSetting.objects.create(
                    name=setting_key,
                    value=settings.SITE_SETTINGS[setting_key]["default"])
                self.stdout.write(self.style.SUCCESS(
                    f'Created setting "{setting_key}"'))
