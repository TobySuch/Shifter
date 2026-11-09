import json
from typing import ClassVar

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from shifter_site_settings.models import SiteSetting
from shifter_site_settings.units import (
    add_expiry_offset,
    describe_expiry_offset,
    parse_file_size,
)

from .models import FileUpload
from .widgets import ShifterDateTimeInput


def default_expiry_datetime():
    """The expiry offered for a new upload, from default_expiry_offset."""
    return add_expiry_offset(
        timezone.now(), SiteSetting.get_setting("default_expiry_offset")
    )


def validate_upload_size(size):
    max_file_size_str = SiteSetting.get_setting("max_file_size")
    if size > parse_file_size(max_file_size_str):
        raise ValidationError(
            f"You can't upload a file larger than {max_file_size_str}",
            code="file-size-too-large",
        )


def clean_upload_expiry(expiry_datetime, enable_expiry):
    """Validate the expiry of a new upload; returns None for no expiry."""
    allow_optional = SiteSetting.get_setting("allow_optional_expiry")

    # If expiry is disabled and optional expiry is allowed, return None
    if not enable_expiry and allow_optional:
        return None

    # If expiry is required (either checkbox is checked OR
    # optional not allowed)
    if not expiry_datetime:
        if allow_optional:
            raise ValidationError(
                "You must provide an expiry date or uncheck "
                "'Set file expiry'.",
                code="expiry-required",
            )
        else:
            raise ValidationError(
                "You must provide an expiry date.",
                code="expiry-required",
            )

    # Validate expiry date is not in the past
    current_datetime = timezone.now()
    if expiry_datetime < current_datetime:
        raise ValidationError(
            "You can't upload a file with an expiry time in the past.",
            code="expiry-time-past",
        )

    # Validate expiry is not too far in the future
    max_expiry_offset = SiteSetting.get_setting("max_expiry_offset")
    try:
        max_expiry_time = add_expiry_offset(
            current_datetime, max_expiry_offset
        )
    except OverflowError:
        # Too far in the future to matter.
        max_expiry_time = None

    if max_expiry_time is not None and expiry_datetime > max_expiry_time:
        raise ValidationError(
            "You can't upload a file with an expiry time more than "
            f"{describe_expiry_offset(max_expiry_offset)} in the future.",
            code="expiry-time-too-far",
        )

    return expiry_datetime


class FileUploadForm(forms.ModelForm):
    enable_expiry = forms.BooleanField(
        required=False, initial=False, label="Set file expiry"
    )

    class Meta:
        model = FileUpload
        fields: ClassVar[list[str]] = [
            "enable_expiry",
            "expiry_datetime",
            "file_content",
        ]
        widgets: ClassVar[dict] = {
            "expiry_datetime": ShifterDateTimeInput(
                attrs={
                    "class": ("input-primary localized-time flex-grow"),
                }
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Check if optional expiry is allowed
        allow_optional = SiteSetting.get_setting("allow_optional_expiry")

        # Always set expiry_datetime as not required initially
        # Validation happens in clean_expiry_datetime based on enable_expiry
        self.fields["expiry_datetime"].required = False

        if not allow_optional:
            # If optional expiry is disabled, hide checkbox
            self.fields["enable_expiry"].widget = forms.HiddenInput()
            self.fields["enable_expiry"].initial = True

        exp_date = default_expiry_datetime()
        exp_date_str = exp_date.strftime(settings.DATETIME_INPUT_FORMATS[0])
        self.fields["expiry_datetime"].initial = exp_date_str

        exp_date_min = timezone.now()
        exp_date_min_str = exp_date_min.strftime(
            settings.DATETIME_INPUT_FORMATS[0]
        )
        self.fields["expiry_datetime"].widget.attrs["min"] = exp_date_min_str
        x_data = (
            "localizedDateTimeInput("
            f"{json.dumps(exp_date.isoformat())}, "
            f"{json.dumps(exp_date_min.isoformat())}"
        )
        exp_date_max = None
        try:
            exp_date_max = add_expiry_offset(
                timezone.now(), SiteSetting.get_setting("max_expiry_offset")
            )
            exp_date_max_str = exp_date_max.strftime(
                settings.DATETIME_INPUT_FORMATS[0]
            )
            self.fields["expiry_datetime"].widget.attrs["max"] = (
                exp_date_max_str
            )
            x_data += f", {json.dumps(exp_date_max.isoformat())})"
        except OverflowError:
            # If the max expiry offset is too large, don't set a max expiry
            # It is too far in the future to matter.
            x_data += ", null)"

        self.fields["expiry_datetime"].widget.attrs["x-data"] = x_data

        # ISO bounds for the React upload island, which renders its own
        # expiry input and converts these to the browser's local time.
        self.expiry_bounds = {
            "initial": exp_date.isoformat(),
            "min": exp_date_min.isoformat(),
            "max": exp_date_max.isoformat() if exp_date_max else None,
        }

    def clean_expiry_datetime(self):
        return clean_upload_expiry(
            self.cleaned_data.get("expiry_datetime"),
            self.cleaned_data.get("enable_expiry", False),
        )

    def clean_file_content(self):
        file_content = self.cleaned_data["file_content"]
        validate_upload_size(file_content.size)
        return file_content


class ChunkedUploadInitForm(forms.Form):
    """Validates the metadata sent before a chunked upload starts."""

    filename = forms.CharField(max_length=255, strip=True)
    size = forms.IntegerField(min_value=0)
    enable_expiry = forms.BooleanField(required=False)
    expiry_datetime = forms.DateTimeField(required=False)

    def clean_filename(self):
        # Match Django's UploadedFile: keep only the base name, whatever
        # path separators the browser sent.
        filename = self.cleaned_data["filename"].replace("\\", "/")
        filename = filename.rsplit("/", 1)[-1].strip()
        if not filename:
            raise ValidationError(
                "A file name is required.", code="filename-required"
            )
        return filename

    def clean_size(self):
        size = self.cleaned_data["size"]
        validate_upload_size(size)
        return size

    def clean_expiry_datetime(self):
        return clean_upload_expiry(
            self.cleaned_data.get("expiry_datetime"),
            self.cleaned_data.get("enable_expiry", False),
        )


class FileExpiryEditForm(forms.ModelForm):
    enable_expiry = forms.BooleanField(
        required=False, initial=False, label="Set file expiry"
    )

    class Meta:
        model = FileUpload
        fields: ClassVar[list[str]] = ["enable_expiry", "expiry_datetime"]
        widgets: ClassVar[dict] = {
            "expiry_datetime": ShifterDateTimeInput(
                attrs={
                    "class": "input-primary localized-time flex-grow",
                }
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        allow_optional = SiteSetting.get_setting("allow_optional_expiry")
        self.fields["expiry_datetime"].required = False

        if not allow_optional:
            self.fields["enable_expiry"].widget = forms.HiddenInput()
            self.fields["enable_expiry"].initial = True
        elif (
            self.instance
            and self.instance.pk
            and self.instance.expiry_datetime
        ):
            self.fields["enable_expiry"].initial = True

        if (
            self.instance
            and self.instance.pk
            and self.instance.expiry_datetime
        ):
            initial_dt = self.instance.expiry_datetime
        else:
            initial_dt = default_expiry_datetime()

        exp_date_min = timezone.now()
        self.fields["expiry_datetime"].initial = initial_dt.strftime(
            settings.DATETIME_INPUT_FORMATS[0]
        )
        self.fields["expiry_datetime"].widget.attrs["min"] = (
            exp_date_min.strftime(settings.DATETIME_INPUT_FORMATS[0])
        )

        x_data = (
            "localizedDateTimeInput("
            f"{json.dumps(initial_dt.isoformat())}, "
            f"{json.dumps(exp_date_min.isoformat())}"
        )
        try:
            exp_date_max = add_expiry_offset(
                timezone.now(), SiteSetting.get_setting("max_expiry_offset")
            )
            self.fields["expiry_datetime"].widget.attrs["max"] = (
                exp_date_max.strftime(settings.DATETIME_INPUT_FORMATS[0])
            )
            x_data += f", {json.dumps(exp_date_max.isoformat())})"
        except OverflowError:
            x_data += ", null)"

        self.fields["expiry_datetime"].widget.attrs["x-data"] = x_data

    def clean_expiry_datetime(self):
        expiry_datetime = self.cleaned_data.get("expiry_datetime")
        enable_expiry = self.cleaned_data.get("enable_expiry", False)
        allow_optional = SiteSetting.get_setting("allow_optional_expiry")

        if not enable_expiry and allow_optional:
            return None

        if not expiry_datetime:
            if allow_optional:
                raise ValidationError(
                    "You must provide an expiry date or uncheck "
                    "'Set file expiry'.",
                    code="expiry-required",
                )
            else:
                raise ValidationError(
                    "You must provide an expiry date.",
                    code="expiry-required",
                )

        current_datetime = timezone.now()
        if expiry_datetime < current_datetime:
            raise ValidationError(
                "You can't set an expiry time in the past.",
                code="expiry-time-past",
            )

        max_expiry_offset = SiteSetting.get_setting("max_expiry_offset")
        try:
            max_expiry_time = add_expiry_offset(
                current_datetime, max_expiry_offset
            )
        except OverflowError:
            # Too far in the future to matter.
            max_expiry_time = None

        if max_expiry_time is not None and expiry_datetime > max_expiry_time:
            raise ValidationError(
                "You can't set an expiry time more than "
                f"{describe_expiry_offset(max_expiry_offset)} in the future.",
                code="expiry-time-too-far",
            )

        return expiry_datetime


class FileSearchForm(forms.Form):
    search = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(
            attrs={
                "class": "input-primary flex-grow",
                "placeholder": "Search files",
            }
        ),
    )
