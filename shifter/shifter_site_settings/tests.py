from datetime import timedelta
from io import StringIO

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.tasks import TaskResultStatus
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from django_tasks_db.models import DBTaskResult

from shifter_files.tasks import calculate_file_hash
from shifter_site_settings.forms import SiteSettingsForm
from shifter_site_settings.models import SiteSetting

TEST_USER_EMAIL = "iama@test.com"
TEST_USER_PASSWORD = "mytemporarypassword"


TEST_USER_EMAIL_2 = "shifter@github.com"
TEST_USER_PASSWORD_2 = "mytemporarypassword"


class SiteSettingsTestCase(TestCase):
    def setUp(self):
        out = StringIO()
        call_command(
            "createsettings",
            "--no-color",
            stdout=out,
        )

    def test_site_settings_created(self):
        max_file_size = SiteSetting.objects.get(name="max_file_size")
        self.assertEqual(
            max_file_size.value,
            settings.SITE_SETTINGS["max_file_size"]["default"],
        )

        default_expiry_offset = SiteSetting.objects.get(
            name="default_expiry_offset"
        )
        self.assertEqual(
            default_expiry_offset.value,
            str(settings.SITE_SETTINGS["default_expiry_offset"]["default"]),
        )

        max_expiry_offset = SiteSetting.objects.get(name="max_expiry_offset")
        self.assertEqual(
            max_expiry_offset.value,
            str(settings.SITE_SETTINGS["max_expiry_offset"]["default"]),
        )


class CreateSiteSettingsCommandTest(TestCase):
    def test_command_output(self):
        expected_output = ""
        for setting_key in settings.SITE_SETTINGS:
            expected_output += f'Created setting "{setting_key}"\n'

        out = StringIO()
        call_command(
            "createsettings",
            "--no-color",
            stdout=out,
        )
        self.assertIn(out.getvalue(), expected_output)


class SiteSettingsViewTest(TestCase):
    def setUp(self):
        out = StringIO()
        call_command(
            "createsettings",
            "--no-color",
            stdout=out,
        )
        User = get_user_model()
        self.super_user = User.objects.create_user(
            TEST_USER_EMAIL, TEST_USER_PASSWORD, is_staff=True
        )
        self.standard_user = User.objects.create_user(
            TEST_USER_EMAIL_2, TEST_USER_PASSWORD_2
        )

    def test_site_settings_view(self):
        # Test submitting the form changes the settings values
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse("shifter_site_settings:site-settings")
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

        # Change setting values
        new_max_file_size = "10MB"
        response = client.post(
            url,
            {
                "setting_max_file_size": new_max_file_size,
                "setting_default_expiry_offset": "1",
                "setting_max_expiry_offset": "2",
                "setting_task_history_retention_days": "0",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            SiteSetting.get_setting("max_file_size"), new_max_file_size
        )
        self.assertEqual(SiteSetting.get_setting("default_expiry_offset"), "1")
        self.assertEqual(SiteSetting.get_setting("max_expiry_offset"), "2")

    def test_new_setup_defaults(self):
        self.assertEqual(SiteSetting.get_setting("max_file_size"), "5GB")
        self.assertEqual(
            SiteSetting.get_setting("default_expiry_offset"), "2W"
        )
        self.assertEqual(SiteSetting.get_setting("max_expiry_offset"), "1M")

    def test_createsettings_keeps_existing_values(self):
        setting = SiteSetting.objects.get(name="max_expiry_offset")
        setting.value = "87600"
        setting.save()
        call_command("createsettings", stdout=StringIO())
        self.assertEqual(
            SiteSetting.get_setting("max_expiry_offset"), "87600"
        )

    def test_site_settings_view_saves_units_normalized(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.post(
            reverse("shifter_site_settings:site-settings"),
            {
                "setting_max_file_size": " 2 gb",
                "setting_default_expiry_offset": "3d",
                "setting_max_expiry_offset": "1 y",
                "setting_task_history_retention_days": "0",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Settings Saved!")
        self.assertEqual(SiteSetting.get_setting("max_file_size"), "2GB")
        self.assertEqual(
            SiteSetting.get_setting("default_expiry_offset"), "3D"
        )
        self.assertEqual(SiteSetting.get_setting("max_expiry_offset"), "1Y")

    def test_site_settings_view_accepts_every_offset_unit(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        for unit in ["H", "D", "W", "M", "Y"]:
            with self.subTest(unit=unit):
                response = client.post(
                    reverse("shifter_site_settings:site-settings"),
                    {
                        "setting_max_file_size": "5GB",
                        "setting_default_expiry_offset": f"1{unit}",
                        "setting_max_expiry_offset": f"2{unit}",
                        "setting_task_history_retention_days": "0",
                    },
                )
                self.assertContains(response, "Settings Saved!")
                self.assertEqual(
                    SiteSetting.get_setting("default_expiry_offset"),
                    f"1{unit}",
                )

    def test_site_settings_view_rejects_invalid_units(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.post(
            reverse("shifter_site_settings:site-settings"),
            {
                "setting_max_file_size": "5TB",
                "setting_default_expiry_offset": "2 fortnights",
                "setting_max_expiry_offset": "1M",
                "setting_task_history_retention_days": "0",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Settings Saved!")
        self.assertContains(
            response, "Enter a whole number followed by KB, MB or GB"
        )
        self.assertContains(response, "W (weeks), M (months) or Y (years)")
        self.assertEqual(SiteSetting.get_setting("max_file_size"), "5GB")
        self.assertEqual(
            SiteSetting.get_setting("default_expiry_offset"), "2W"
        )

    def test_site_settings_view_rejects_unrepresentable_default(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.post(
            reverse("shifter_site_settings:site-settings"),
            {
                "setting_max_file_size": "5GB",
                "setting_default_expiry_offset": "100000Y",
                "setting_max_expiry_offset": "1M",
                "setting_task_history_retention_days": "0",
            },
        )
        self.assertContains(response, "This offset is too far in the future.")
        self.assertEqual(
            SiteSetting.get_setting("default_expiry_offset"), "2W"
        )

    def get_settings_page(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        return client.get(reverse("shifter_site_settings:site-settings"))

    def test_task_log_is_collapsed_and_lists_tasks(self):
        result = calculate_file_hash.enqueue(999)
        DBTaskResult.objects.filter(id=result.id).update(
            status=TaskResultStatus.FAILED,
            exception_class_path="builtins.PermissionError",
        )

        response = self.get_settings_page()

        self.assertContains(response, '<details id="task-log"')
        content = response.content.decode()
        details_tag = content.split('<details id="task-log"')[1].split(">")[0]
        self.assertNotIn(" open", details_tag)
        self.assertContains(response, "1 task")
        self.assertContains(response, "Calculate file hash")
        self.assertContains(response, "File #999 (deleted)")
        self.assertContains(response, "Failed")
        self.assertContains(response, "PermissionError")

    def test_task_log_shows_when_a_task_finished(self):
        finished_at = timezone.now() - timedelta(hours=1)
        result = calculate_file_hash.enqueue(999)
        DBTaskResult.objects.filter(id=result.id).update(
            status=TaskResultStatus.SUCCESSFUL,
            started_at=finished_at - timedelta(seconds=1),
            finished_at=finished_at,
        )

        response = self.get_settings_page()

        self.assertContains(
            response, f"localizedTime('{finished_at.isoformat()}')"
        )

    def test_task_log_empty(self):
        response = self.get_settings_page()

        self.assertContains(response, "No background tasks have run yet.")

    def test_task_log_says_when_only_latest_are_shown(self):
        for _ in range(51):
            calculate_file_hash.enqueue(999)

        response = self.get_settings_page()

        self.assertContains(response, "latest 50 of 51 tasks")
        self.assertEqual(
            response.content.decode().count("Calculate file hash"), 50
        )

    def test_site_information_shows_task_stats(self):
        for status in (
            TaskResultStatus.READY,
            TaskResultStatus.READY,
            TaskResultStatus.RUNNING,
            TaskResultStatus.FAILED,
        ):
            result = calculate_file_hash.enqueue(999)
            DBTaskResult.objects.filter(id=result.id).update(
                status=status, finished_at=timezone.now()
            )

        response = self.get_settings_page()

        self.assertEqual(response.context["task_stats"].waiting, 2)
        self.assertContains(response, "Queued Tasks")
        self.assertContains(response, "Failed Tasks")
        self.assertContains(response, "1 running")
        self.assertContains(response, "Last task finished")
        clipboard = response.context["site_information_clipboard"]
        self.assertIn("Tasks Waiting: 2", clipboard)
        self.assertIn("Tasks Running: 1", clipboard)
        self.assertIn("Failed Tasks: 1", clipboard)
        self.assertNotIn("Awaiting Hash", clipboard)
        self.assertIn("Last Task Finished: ", clipboard)

    def test_scheduled_tasks_are_shown_as_scheduled(self):
        run_after = timezone.now() + timedelta(days=3)
        calculate_file_hash.using(run_after=run_after).enqueue(999)

        response = self.get_settings_page()

        self.assertContains(response, "Scheduled")
        self.assertContains(response, run_after.isoformat()[:16])
        self.assertContains(response, "1 scheduled")
        self.assertEqual(response.context["task_stats"].waiting, 0)
        self.assertIn(
            "Tasks Scheduled: 1",
            response.context["site_information_clipboard"],
        )

    def test_site_information_when_no_tasks_have_finished(self):
        response = self.get_settings_page()

        self.assertContains(response, "No task has finished yet.")
        self.assertIn(
            "Last Task Finished: Never",
            response.context["site_information_clipboard"],
        )

    def test_maintenance_buttons_rendered(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_site_settings:site-settings"))
        content = response.content.decode()
        # They live in their own Maintenance section below the settings
        # form, above Site Information.
        form_end = content.index("</form>")
        maintenance = content.index("<h2", form_end)
        site_info = content.index("Site Information")
        self.assertIn("Maintenance", content[maintenance:site_info])
        for button_id in (
            "prune-task-results-btn",
            "cleanup-expired-files-btn",
        ):
            position = content.index(f'id="{button_id}" type="button"')
            self.assertTrue(maintenance < position < site_info, button_id)

    def test_standard_user_cannot_access(self):
        # Test that a standard user cannot access the site settings page
        client = Client()
        client.login(email=TEST_USER_EMAIL_2, password=TEST_USER_PASSWORD_2)
        url = reverse("shifter_site_settings:site-settings")
        response = client.get(url)
        self.assertEqual(response.status_code, 403)

    # #427 - Setting max expiry date in hours to large number causes 500 error
    # when accessing file upload page.
    def test_max_expiry_limits(self):
        # Test submitting the form changes the settings values
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse("shifter_site_settings:site-settings")
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

        # Change setting values
        old_setting_max_expiry_offset = SiteSetting.get_setting(
            "max_expiry_offset"
        )
        setting_max_expiry_offset = "99999999999999999999999999999999999999"
        response = client.post(
            url,
            {
                "setting_max_file_size": "5120MB",
                "setting_default_expiry_offset": "336",
                "setting_max_expiry_offset": setting_max_expiry_offset,
                "setting_task_history_retention_days": "0",
            },
        )
        self.assertEqual(response.status_code, 200)
        # Check response contains error
        self.assertContains(
            response,
"Maximum value: 2147483647",
        )

        # Check that the setting was not changed
        self.assertEqual(
            SiteSetting.get_setting("max_expiry_offset"),
            old_setting_max_expiry_offset,
        )


class SiteSettingsSiteInformationTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.super_user = User.objects.create_user(
            TEST_USER_EMAIL, TEST_USER_PASSWORD, is_staff=True
        )


class SiteSettingFieldTypesTestCase(TestCase):
    """Test different field types and conversions for site settings."""

    def setUp(self):
        """Initialize test settings."""
        # Create test users
        User = get_user_model()
        User.objects.create_user(
            email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD, is_staff=True
        )
        # Initialize settings from defaults
        call_command("createsettings")

    def test_boolean_setting_default_value(self):
        """Test that boolean setting returns correct default value."""
        # Should return boolean False, not string "False"
        result = SiteSetting.get_setting("allow_optional_expiry")
        self.assertIsInstance(result, bool)
        self.assertEqual(result, False)

    def test_boolean_setting_string_true_conversion(self):
        """Test that string 'True' converts to boolean True."""
        setting = SiteSetting.objects.get(name="allow_optional_expiry")
        setting.value = "True"
        setting.save()

        result = SiteSetting.get_setting("allow_optional_expiry")
        self.assertIsInstance(result, bool)
        self.assertEqual(result, True)

    def test_boolean_setting_string_false_conversion(self):
        """Test that string 'False' converts to boolean False."""
        setting = SiteSetting.objects.get(name="allow_optional_expiry")
        setting.value = "False"
        setting.save()

        result = SiteSetting.get_setting("allow_optional_expiry")
        self.assertIsInstance(result, bool)
        self.assertEqual(result, False)

    def test_boolean_setting_case_insensitive(self):
        """Test that boolean conversion is case-insensitive."""
        setting = SiteSetting.objects.get(name="allow_optional_expiry")

        # Test various casings
        for value in ["true", "TRUE", "True", "tRuE"]:
            setting.value = value
            setting.save()
            result = SiteSetting.get_setting("allow_optional_expiry")
            self.assertEqual(result, True, f"Failed for value: {value}")

    def test_boolean_setting_numeric_one_is_true(self):
        """Test that string '1' converts to boolean True."""
        setting = SiteSetting.objects.get(name="allow_optional_expiry")
        setting.value = "1"
        setting.save()

        result = SiteSetting.get_setting("allow_optional_expiry")
        self.assertEqual(result, True)

    def test_boolean_setting_other_values_are_false(self):
        """Test that non-true values convert to boolean False."""
        setting = SiteSetting.objects.get(name="allow_optional_expiry")

        # Test various "falsy" strings
        for value in ["0", "false", "FALSE", "no", "off", ""]:
            setting.value = value
            setting.save()
            result = SiteSetting.get_setting("allow_optional_expiry")
            self.assertEqual(result, False, f"Failed for value: {value}")

    def test_char_field_returns_string(self):
        """Test that CharField setting returns string value."""
        result = SiteSetting.get_setting("max_file_size")
        self.assertIsInstance(result, str)
        self.assertEqual(result, "5GB")

    def test_expiry_offset_field_returns_string(self):
        """Test that an expiry offset setting returns its string value."""
        # Units are parsed by the consuming code (add_expiry_offset)
        result = SiteSetting.get_setting("default_expiry_offset")
        self.assertIsInstance(result, str)
        self.assertEqual(result, "2W")

    def test_boolean_form_field_initial_true(self):
        """Test boolean form field initializes with True."""
        setting = SiteSetting.objects.get(name="allow_optional_expiry")
        setting.value = "True"
        setting.save()

        form = SiteSettingsForm()
        field = form.fields["setting_allow_optional_expiry"]

        self.assertIsInstance(field, forms.BooleanField)
        self.assertEqual(field.initial, True)
        self.assertEqual(field.required, False)

    def test_boolean_form_field_initial_false(self):
        """Test boolean form field initializes with False."""
        setting = SiteSetting.objects.get(name="allow_optional_expiry")
        setting.value = "False"
        setting.save()

        form = SiteSettingsForm()
        field = form.fields["setting_allow_optional_expiry"]

        self.assertEqual(field.initial, False)

    def test_boolean_view_save_checked(self):
        """Test that checking boolean toggle saves as 'True'."""
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)

        # Submit form with checkbox checked (True)
        response = client.post(
            reverse("shifter_site_settings:site-settings"),
            {
                "setting_max_file_size": "5120MB",
                "setting_default_expiry_offset": str(24 * 14),
                "setting_max_expiry_offset": str(24 * 365 * 5),
                "setting_task_history_retention_days": "0",
                "setting_allow_optional_expiry": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        setting = SiteSetting.objects.get(name="allow_optional_expiry")
        # Should be stored as string "True"
        self.assertEqual(setting.value, "True")
        # get_setting should return boolean True
        self.assertEqual(
            SiteSetting.get_setting("allow_optional_expiry"), True
        )

    def test_boolean_view_save_unchecked(self):
        """Test that unchecking boolean toggle saves as 'False'."""
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)

        # First set to True
        setting = SiteSetting.objects.get(name="allow_optional_expiry")
        setting.value = "True"
        setting.save()

        # Submit form with checkbox unchecked (omitted from POST data)
        response = client.post(
            reverse("shifter_site_settings:site-settings"),
            {
                "setting_max_file_size": "5120MB",
                "setting_default_expiry_offset": str(24 * 14),
                "setting_max_expiry_offset": str(24 * 365 * 5),
                "setting_task_history_retention_days": "0",
                # setting_allow_optional_expiry omitted = unchecked
            },
        )

        self.assertEqual(response.status_code, 200)
        setting.refresh_from_db()
        # Should be stored as string "False"
        self.assertEqual(setting.value, "False")
        # get_setting should return boolean False
        self.assertEqual(
            SiteSetting.get_setting("allow_optional_expiry"), False
        )

    def test_boolean_form_renders_checkbox_widget(self):
        """Test that boolean field uses checkbox widget in form."""
        form = SiteSettingsForm()
        field = form.fields["setting_allow_optional_expiry"]

        # Check widget type
        self.assertEqual(field.widget.input_type, "checkbox")

    def test_all_setting_types_persist_correctly(self):
        """Integration test: all field types save and retrieve."""
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)

        # Submit form with all fields
        response = client.post(
            reverse("shifter_site_settings:site-settings"),
            {
                "setting_max_file_size": "10240MB",  # CharField
                "setting_default_expiry_offset": "720",  # ExpiryOffsetField
                "setting_max_expiry_offset": "87600",  # ExpiryOffsetField
                "setting_task_history_retention_days": "0",
                "setting_allow_optional_expiry": "on",  # BooleanField
            },
        )

        self.assertEqual(response.status_code, 200)

        # Verify CharField
        self.assertEqual(SiteSetting.get_setting("max_file_size"), "10240MB")

        # Verify ExpiryOffsetField (a bare number is kept as hours)
        self.assertEqual(
            SiteSetting.get_setting("default_expiry_offset"), "720"
        )

        # Verify BooleanField (returns boolean)
        self.assertEqual(
            SiteSetting.get_setting("allow_optional_expiry"), True
        )
