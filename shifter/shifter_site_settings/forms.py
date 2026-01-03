from django import forms
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator

from .models import SiteSetting


class SiteSettingsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for setting in SiteSetting.objects.all():
            setting_config: dict = settings.SITE_SETTINGS[setting.name]
            label = setting_config["label"]
            form_field_type = setting_config.get("field_type", forms.CharField)

            # Handle BooleanField initialization differently
            if form_field_type == forms.BooleanField:
                # Convert string value from DB to boolean for initial state
                initial_value = str(setting.value).lower() in ["true", "1"]
                self.fields[f"setting_{setting.name}"] = form_field_type(
                    label=label,
                    initial=initial_value,
                    required=False,  # Checkboxes should not be required
                )
            else:
                # Existing behavior for other field types
                self.fields[f"setting_{setting.name}"] = form_field_type(
                    label=label, initial=setting.value
                )

            if "tooltip" in setting_config:
                self.fields[
                    f"setting_{setting.name}"
                ].help_text = setting_config["tooltip"]
            if "min_value" in setting_config:
                self.fields[f"setting_{setting.name}"].validators.append(
                    MinValueValidator(
                        setting_config["min_value"],
                        "Minimum value: %(limit_value)s",
                    )
                )
            if "max_value" in setting_config:
                self.fields[f"setting_{setting.name}"].validators.append(
                    MaxValueValidator(
                        setting_config["max_value"],
                        "Maximum value: %(limit_value)s",
                    )
                )
