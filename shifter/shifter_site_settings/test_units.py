from datetime import UTC, datetime, timedelta

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from shifter_site_settings.fields import ExpiryOffsetField, FileSizeField
from shifter_site_settings.units import (
    add_expiry_offset,
    describe_expiry_offset,
    normalize_expiry_offset,
    normalize_file_size,
    parse_file_size,
)

START = datetime(2026, 1, 31, 12, 0, tzinfo=UTC)


class ParseFileSizeTests(SimpleTestCase):
    def test_units(self):
        self.assertEqual(parse_file_size("100"), 100)
        self.assertEqual(parse_file_size("1KB"), 1024)
        self.assertEqual(parse_file_size("5120MB"), 5120 * 1024**2)
        self.assertEqual(parse_file_size("5GB"), 5 * 1024**3)

    def test_gb_matches_equivalent_mb(self):
        self.assertEqual(parse_file_size("5GB"), parse_file_size("5120MB"))

    def test_case_and_spaces_ignored(self):
        self.assertEqual(parse_file_size(" 2 gb "), 2 * 1024**3)
        self.assertEqual(normalize_file_size(" 2 gb "), "2GB")

    def test_invalid(self):
        for value in ["", "GB", "1.5GB", "5TB", "-1MB", "5 G B"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_file_size(value)


class ExpiryOffsetTests(SimpleTestCase):
    def test_no_unit_is_hours(self):
        self.assertEqual(
            add_expiry_offset(START, "336"), START + timedelta(hours=336)
        )
        self.assertEqual(
            add_expiry_offset(START, 336), START + timedelta(hours=336)
        )

    def test_hours_days_weeks(self):
        self.assertEqual(
            add_expiry_offset(START, "5H"), START + timedelta(hours=5)
        )
        self.assertEqual(
            add_expiry_offset(START, "3D"), START + timedelta(days=3)
        )
        self.assertEqual(
            add_expiry_offset(START, "2W"), START + timedelta(weeks=2)
        )

    def test_months_are_calendar_months(self):
        self.assertEqual(
            add_expiry_offset(START, "1M"),
            datetime(2026, 2, 28, 12, 0, tzinfo=UTC),
        )
        self.assertEqual(
            add_expiry_offset(START, "13M"),
            datetime(2027, 2, 28, 12, 0, tzinfo=UTC),
        )
        self.assertEqual(
            add_expiry_offset(START, "11M"),
            datetime(2026, 12, 31, 12, 0, tzinfo=UTC),
        )

    def test_years_are_calendar_years(self):
        leap_day = datetime(2028, 2, 29, tzinfo=UTC)
        self.assertEqual(
            add_expiry_offset(leap_day, "1Y"),
            datetime(2029, 2, 28, tzinfo=UTC),
        )
        self.assertEqual(
            add_expiry_offset(START, "5Y"),
            datetime(2031, 1, 31, 12, 0, tzinfo=UTC),
        )

    def test_case_and_spaces_ignored(self):
        self.assertEqual(
            add_expiry_offset(START, " 2 w "), START + timedelta(weeks=2)
        )
        self.assertEqual(normalize_expiry_offset(" 2 w "), "2W")
        self.assertEqual(normalize_expiry_offset("336"), "336")

    def test_too_large_raises_overflow(self):
        for value in ["2147483647", "2147483647D", "99999M", "10000Y"]:
            with (
                self.subTest(value=value),
                self.assertRaises(OverflowError),
            ):
                add_expiry_offset(START, value)

    def test_invalid(self):
        for value in ["", "W", "1.5W", "2X", "-1D", "2 weeks"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                add_expiry_offset(START, value)

    def test_describe(self):
        self.assertEqual(describe_expiry_offset("336"), "336 hours")
        self.assertEqual(describe_expiry_offset("1H"), "1 hour")
        self.assertEqual(describe_expiry_offset("1D"), "1 day")
        self.assertEqual(describe_expiry_offset("2W"), "2 weeks")
        self.assertEqual(describe_expiry_offset("1M"), "1 month")
        self.assertEqual(describe_expiry_offset("3Y"), "3 years")


class FieldTests(SimpleTestCase):
    def test_file_size_field_normalizes(self):
        self.assertEqual(FileSizeField().clean("5 gb"), "5GB")
        self.assertEqual(FileSizeField().clean("5120MB"), "5120MB")

    def test_file_size_field_rejects_invalid(self):
        with self.assertRaises(ValidationError):
            FileSizeField().clean("5TB")

    def test_expiry_offset_field_normalizes(self):
        self.assertEqual(ExpiryOffsetField().clean("2w"), "2W")
        self.assertEqual(ExpiryOffsetField().clean("1 m"), "1M")
        self.assertEqual(ExpiryOffsetField().clean("336"), "336")

    def test_expiry_offset_field_rejects_invalid(self):
        with self.assertRaises(ValidationError):
            ExpiryOffsetField().clean("2 fortnights")

    def test_expiry_offset_field_max_amount(self):
        self.assertEqual(
            ExpiryOffsetField().clean("2147483647"), "2147483647"
        )
        with self.assertRaisesMessage(
            ValidationError, "Maximum value: 2147483647"
        ):
            ExpiryOffsetField().clean("2147483648Y")
