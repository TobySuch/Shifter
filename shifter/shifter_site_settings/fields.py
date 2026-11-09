from django import forms
from django.core.exceptions import ValidationError

from .units import (
    normalize_expiry_offset,
    normalize_file_size,
    split_expiry_offset,
)

# Largest number accepted in an expiry offset, whatever its unit.
MAX_EXPIRY_OFFSET_AMOUNT = 2147483647


class FileSizeField(forms.CharField):
    """A file size such as "5GB", saved in canonical form."""

    def clean(self, value):
        value = super().clean(value)
        try:
            return normalize_file_size(value)
        except ValueError:
            raise ValidationError(
                "Enter a whole number followed by KB, MB or GB, "
                "e.g. 5GB.",
                code="invalid-file-size",
            ) from None


class ExpiryOffsetField(forms.CharField):
    """An expiry offset such as "2W", saved in canonical form. A number
    without a unit is hours."""

    def clean(self, value):
        value = super().clean(value)
        try:
            amount, _unit = split_expiry_offset(value)
        except ValueError:
            raise ValidationError(
                "Enter a whole number followed by H (hours), D (days), "
                "W (weeks), M (months) or Y (years), e.g. 2W. A number "
                "without a unit is hours.",
                code="invalid-expiry-offset",
            ) from None
        if amount > MAX_EXPIRY_OFFSET_AMOUNT:
            raise ValidationError(
                "Maximum value: %(limit_value)s",
                code="max_value",
                params={"limit_value": MAX_EXPIRY_OFFSET_AMOUNT},
            )
        return normalize_expiry_offset(value)
