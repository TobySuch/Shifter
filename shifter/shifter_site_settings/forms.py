from django import forms
from django.conf import settings

from .models import SiteSetting


class SiteSettingsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for setting in SiteSetting.objects.all():
            label = settings.SITE_SETTINGS[setting.name]["label"]
            self.fields[f"setting_{setting.name}"] = forms.CharField(
                label=label, initial=setting.value
            )
