from django import forms
from django.conf import settings

from .models import SiteSetting


class SiteSettingsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for setting in SiteSetting.objects.all():
            setting_config: dict = settings.SITE_SETTINGS[setting.name]
            label = setting_config["label"]
            form_field_type = setting_config.get("field_type",
                                                 forms.CharField)
            self.fields[f"setting_{setting.name}"] = form_field_type(
                label=label, initial=setting.value
            )
            if "tooltip" in setting_config:
                self.fields[f"setting_{setting.name}"].help_text = \
                    setting_config["tooltip"]
