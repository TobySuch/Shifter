"""Parsing for site settings that carry units.

File sizes are a whole number followed by KB, MB or GB (no unit means
bytes). Expiry offsets are a whole number followed by H (hours), D (days),
W (weeks), M (months) or Y (years); no unit means hours, which is how
offsets were stored before units were supported. Units are case-insensitive
and may be separated from the number by spaces.
"""

import calendar
import re
from datetime import datetime, timedelta

_VALUE_RE = re.compile(r"^\s*(\d+)\s*([A-Za-z]*)\s*$")

FILE_SIZE_UNITS = {
    "": 1,
    "KB": 1024,
    "MB": 1024**2,
    "GB": 1024**3,
}

# Unit letter -> (singular name, plural name)
EXPIRY_OFFSET_UNITS = {
    "H": ("hour", "hours"),
    "D": ("day", "days"),
    "W": ("week", "weeks"),
    "M": ("month", "months"),
    "Y": ("year", "years"),
}
DEFAULT_EXPIRY_OFFSET_UNIT = "H"


def _split(value, units, kind):
    match = _VALUE_RE.match(str(value))
    if not match:
        raise ValueError(f"Invalid {kind}: {value!r}")
    amount, unit = int(match.group(1)), match.group(2).upper()
    if unit not in units:
        raise ValueError(f"Unknown {kind} unit: {match.group(2)!r}")
    return amount, unit


def split_file_size(value):
    """Return (amount, unit) for a file size such as "5GB"; unit may be ""."""
    return _split(value, FILE_SIZE_UNITS, "file size")


def parse_file_size(value):
    """Convert a file size such as "5120MB", "5GB" or "1KB" to bytes."""
    amount, unit = split_file_size(value)
    return amount * FILE_SIZE_UNITS[unit]


def normalize_file_size(value):
    """Canonical form of a file size, e.g. " 5 gb" -> "5GB"."""
    amount, unit = split_file_size(value)
    return f"{amount}{unit}"


def _split_expiry_offset(value):
    return _split(value, {**EXPIRY_OFFSET_UNITS, "": None}, "expiry offset")


def split_expiry_offset(value):
    """Return (amount, unit) for an offset such as "2W" or "336"."""
    amount, unit = _split_expiry_offset(value)
    return amount, unit or DEFAULT_EXPIRY_OFFSET_UNIT


def normalize_expiry_offset(value):
    """Canonical form of an offset, e.g. "2 w" -> "2W"; "336" is kept."""
    amount, unit = _split_expiry_offset(value)
    return f"{amount}{unit}"


def describe_expiry_offset(value):
    """Human readable offset, e.g. "2W" -> "2 weeks", "1" -> "1 hour"."""
    amount, unit = split_expiry_offset(value)
    singular, plural = EXPIRY_OFFSET_UNITS[unit]
    return f"{amount} {singular if amount == 1 else plural}"


def _add_months(start, months):
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    if year > datetime.max.year:
        raise OverflowError("date value out of range")
    month = month_index % 12 + 1
    # Clamp to the last day of the month, e.g. 31 Jan + 1M -> 28/29 Feb.
    day = min(start.day, calendar.monthrange(year, month)[1])
    return start.replace(year=year, month=month, day=day)


def add_expiry_offset(start, value):
    """Return start plus the offset. Months and years are calendar months
    and years. Raises OverflowError if the result is out of range."""
    amount, unit = split_expiry_offset(value)
    if unit == "M":
        return _add_months(start, amount)
    if unit == "Y":
        return _add_months(start, amount * 12)
    hours = {"H": 1, "D": 24, "W": 24 * 7}[unit] * amount
    return start + timedelta(hours=hours)
