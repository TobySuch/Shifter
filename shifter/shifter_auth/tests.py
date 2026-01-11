from django.contrib.auth import get_user, get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from shifter_auth.middleware import (
    ensure_first_time_setup_completed,
    is_first_time_setup_required,
)
from shifter_files.models import FileUpload

TEST_USER_EMAIL = "iama@test.com"
TEST_STAFF_USER_EMAIL = "iamastaff@test.com"
TEST_ADDITIONAL_USER_EMAIL = "iamalsoa@test.com"
TEST_USER_PASSWORD = "mytemporarypassword"
TEST_USER_NEW_PASSWORD = "mynewpassword"

TEST_FILE_NAME = "mytestfile.txt"
TEST_FILE_CONTENT = b"Hello, World!"

DATETIME_DISPLAY_FORMAT = "%b %-d, %Y, %-I:%M %p"  # Feb 6, 2021, 12:00 AM


def format_datetime(dt):
    return dt.strftime(DATETIME_DISPLAY_FORMAT)


class IndexViewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        User.objects.create_user(TEST_USER_EMAIL, TEST_USER_PASSWORD)

    def test_logout_unauthenticated(self):
        client = Client()
        response = client.post(reverse("shifter_auth:logout"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, reverse("shifter_auth:login") + "?next=/auth/logout"
        )

    def test_logout_with_get_request(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_auth:logout"))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(get_user(client).is_authenticated)

    def test_logout_authenticated(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.post(reverse("shifter_auth:logout"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("shifter_files:index"))
        self.assertFalse(get_user(client).is_authenticated)


class EnsurePasswordResetMiddlewareTest(TestCase):
    def setUp(self):
        User = get_user_model()
        user = User.objects.create_user(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        user.change_password_on_login = True
        user.save()

    def test_redirect(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_files:index"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("shifter_auth:settings"))

    def test_allow_logout(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.post(reverse("shifter_auth:logout"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("shifter_files:index"))
        self.assertFalse(get_user(client).is_authenticated)

    def test_allow_password_reset(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_auth:settings"))
        self.assertEqual(response.status_code, 200)


class ChangePasswordViewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        user = User.objects.create_user(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        user.save()

    def test_page_load(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_auth:settings"))
        self.assertEqual(response.status_code, 200)

    def test_successful_form_submit(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.post(
            reverse("shifter_auth:settings"),
            {
                "new_password": TEST_USER_NEW_PASSWORD,
                "confirm_password": TEST_USER_NEW_PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("shifter_files:index"))
        self.assertFalse(get_user(client).is_authenticated)

        # Ensure login with old password fails
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        self.assertFalse(get_user(client).is_authenticated)

        client.login(email=TEST_USER_EMAIL, password=TEST_USER_NEW_PASSWORD)
        self.assertTrue(get_user(client).is_authenticated)

    def test_unsuccessful_form_submit(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.post(
            reverse("shifter_auth:settings"),
            {
                "new_password": TEST_USER_NEW_PASSWORD,
                "confirm_password": TEST_USER_NEW_PASSWORD + "wrong",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertInHTML("Passwords do not match!", response.content.decode())


class CreateNewUserViewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        user = User.objects.create_user(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        user.save()
        staff_user = User.objects.create_user(
            TEST_STAFF_USER_EMAIL, TEST_USER_PASSWORD, is_staff=True
        )
        staff_user.save()

    def test_page_load_not_staff(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_auth:create-new-user"))
        self.assertEqual(response.status_code, 403)
        self.assertInHTML(
            "You do not have access to create new users."
            " Please ask an administrator for assistance.",
            response.content.decode(),
        )

    def test_page_load(self):
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_auth:create-new-user"))
        self.assertEqual(response.status_code, 200)

    def test_create_new_user(self):
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.post(
            reverse("shifter_auth:create-new-user"),
            {
                "email": TEST_ADDITIONAL_USER_EMAIL,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("new_password", response.context)

        User = get_user_model()
        users = User.objects.filter(email=TEST_ADDITIONAL_USER_EMAIL)
        self.assertEqual(users.count(), 1)
        self.assertTrue(users[0].change_password_on_login)

        # Verify the generated password works
        new_password = response.context["new_password"]
        client2 = Client()
        self.assertTrue(
            client2.login(
                email=TEST_ADDITIONAL_USER_EMAIL, password=new_password
            )
        )

    def test_new_user_already_exists(self):
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.post(
            reverse("shifter_auth:create-new-user"),
            {
                "email": TEST_USER_EMAIL,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertInHTML("Email already taken!", response.content.decode())

        User = get_user_model()
        self.assertEqual(User.objects.filter(email=TEST_USER_EMAIL).count(), 1)

    def test_new_user_not_staff(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.post(
            reverse("shifter_auth:create-new-user"),
            {
                "email": TEST_ADDITIONAL_USER_EMAIL,
            },
        )
        self.assertEqual(response.status_code, 403)

        User = get_user_model()
        self.assertEqual(
            User.objects.filter(email=TEST_ADDITIONAL_USER_EMAIL).count(), 0
        )


class FirstTimeSetupTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_is_first_time_setup_required_true(self):
        User = get_user_model()
        User.objects.all().delete()
        self.assertTrue(is_first_time_setup_required())

    def test_is_first_time_setup_required_false(self):
        User = get_user_model()
        User.objects.create_user(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        self.assertFalse(is_first_time_setup_required())

    def test_ensure_first_time_setup_completed_redirect(self):
        User = get_user_model()
        User.objects.all().delete()

        middleware = ensure_first_time_setup_completed(lambda request: None)
        request = self.factory.get(reverse("shifter_files:index"))
        response = middleware(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, reverse("shifter_auth:first-time-setup")
        )

    def test_ensure_first_time_setup_completed_no_redirect(self):
        User = get_user_model()
        User.objects.create_user(
            TEST_ADDITIONAL_USER_EMAIL, TEST_USER_PASSWORD
        )
        middleware = ensure_first_time_setup_completed(lambda request: None)
        request = self.factory.get(reverse("shifter_files:index"))
        request.user = get_user_model().objects.create_user(
            TEST_USER_EMAIL, TEST_USER_PASSWORD
        )
        response = middleware(request)
        self.assertIsNone(response)


class UserListViewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.regular_user = User.objects.create_user(
            TEST_USER_EMAIL, TEST_USER_PASSWORD
        )
        self.staff_user = User.objects.create_user(
            TEST_STAFF_USER_EMAIL, TEST_USER_PASSWORD, is_staff=True
        )

    def test_list_requires_login(self):
        client = Client()
        response = client.get(reverse("shifter_auth:user-list"))
        self.assertEqual(response.status_code, 302)

    def test_list_requires_staff(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_auth:user-list"))
        self.assertEqual(response.status_code, 403)

    def test_list_accessible_by_staff(self):
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_auth:user-list"))
        self.assertEqual(response.status_code, 200)

    def test_list_displays_users(self):
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_auth:user-list"))
        self.assertContains(response, TEST_USER_EMAIL)
        self.assertContains(response, TEST_STAFF_USER_EMAIL)

    def test_search_users(self):
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(
            reverse("shifter_auth:user-list") + "?search=iamastaff"
        )
        self.assertContains(response, TEST_STAFF_USER_EMAIL)
        self.assertNotContains(response, TEST_USER_EMAIL)

    @override_settings(MEDIA_ROOT="/tmp/test_media")
    def test_list_shows_active_files_count(self):
        """Test that user list displays count of active files."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from shifter_files.models import FileUpload

        # Create active files for regular user
        for i in range(3):
            file_content = SimpleUploadedFile(
                f"test_file_{i}.txt",
                b"Test content",
                content_type="text/plain",
            )
            FileUpload.objects.create(
                owner=self.regular_user,
                filename=f"test_file_{i}.txt",
                upload_datetime=timezone.now(),
                expiry_datetime=timezone.now() + timezone.timedelta(days=7),
                file_content=file_content,
            )

        # Create expired file for regular user (should not be counted)
        expired_file = SimpleUploadedFile(
            "expired.txt", b"Expired", content_type="text/plain"
        )
        FileUpload.objects.create(
            owner=self.regular_user,
            filename="expired.txt",
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() - timezone.timedelta(days=1),
            file_content=expired_file,
        )

        # Create 1 active file for staff user
        staff_file = SimpleUploadedFile(
            "staff.txt", b"Staff", content_type="text/plain"
        )
        FileUpload.objects.create(
            owner=self.staff_user,
            filename="staff.txt",
            upload_datetime=timezone.now(),
            expiry_datetime=timezone.now() + timezone.timedelta(days=7),
            file_content=staff_file,
        )

        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_auth:user-list"))

        # Verify response contains the active file counts
        self.assertContains(response, "Active Files")
        # Regular user should have 3 active files (not 4)
        content = response.content.decode()
        self.assertIn(">3<", content)
        # Staff user should have 1 active file
        self.assertIn(">1<", content)


class UserDetailViewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.regular_user = User.objects.create_user(
            TEST_USER_EMAIL, TEST_USER_PASSWORD
        )
        self.staff_user = User.objects.create_user(
            TEST_STAFF_USER_EMAIL, TEST_USER_PASSWORD, is_staff=True
        )

    def test_detail_requires_login(self):
        client = Client()
        url = reverse(
            "shifter_auth:user-detail", kwargs={"pk": self.regular_user.pk}
        )
        response = client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_detail_requires_staff(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_auth:user-detail", kwargs={"pk": self.regular_user.pk}
        )
        response = client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_detail_accessible_by_staff(self):
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_auth:user-detail", kwargs={"pk": self.regular_user.pk}
        )
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_edit_user_details(self):
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_auth:user-detail", kwargs={"pk": self.regular_user.pk}
        )
        response = client.post(
            url,
            {
                "email": "newemail@test.com",
                "is_staff": False,
                "is_active": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.email, "newemail@test.com")

    def test_cannot_remove_own_staff_status(self):
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_auth:user-detail", kwargs={"pk": self.staff_user.pk}
        )
        client.post(
            url,
            {
                "email": TEST_STAFF_USER_EMAIL,
                "is_staff": False,  # Trying to remove own staff status
                "is_active": True,
            },
        )
        self.staff_user.refresh_from_db()
        self.assertTrue(self.staff_user.is_staff)  # Should still be staff

    def test_toggle_user_admin_status(self):
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)

        # Make regular user an admin
        url = reverse(
            "shifter_auth:user-detail", kwargs={"pk": self.regular_user.pk}
        )
        client.post(
            url,
            {
                "email": TEST_USER_EMAIL,
                "is_staff": True,
                "is_active": True,
            },
        )
        self.regular_user.refresh_from_db()
        self.assertTrue(self.regular_user.is_staff)

    def test_reset_password_hidden_for_self(self):
        """Test reset password button hidden for own account."""
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_auth:user-detail", kwargs={"pk": self.staff_user.pk}
        )
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

        # Verify "Reset Password" button is NOT present
        self.assertNotIn("Reset Password", response.content.decode())

        # Verify "Go to Settings" link IS present
        self.assertIn("Go to Settings", response.content.decode())
        self.assertIn("Change Your Password", response.content.decode())

    def test_reset_password_shown_for_other_user(self):
        """Test that reset password button is shown when viewing other user."""
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_auth:user-detail", kwargs={"pk": self.regular_user.pk}
        )
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

        # Verify "Reset Password" button IS present
        self.assertIn("Reset Password", response.content.decode())

        # Verify "Delete User" button IS present
        self.assertIn("Delete User", response.content.decode())

        # Verify "Actions" header IS present
        self.assertIn("Actions", response.content.decode())

        # Verify settings link is NOT present
        self.assertNotIn("Go to Settings", response.content.decode())
        self.assertNotIn("Change Your Password", response.content.decode())

    def test_user_detail_shows_help_text(self):
        """Test that help text for toggles is displayed."""
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_auth:user-detail", kwargs={"pk": self.regular_user.pk}
        )
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()
        # Verify administrator help text
        self.assertIn("Can manage users and change site settings", content)
        # Verify active help text
        self.assertIn("Inactive users cannot log in", content)


class UserDeleteViewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.regular_user = User.objects.create_user(
            TEST_USER_EMAIL, TEST_USER_PASSWORD
        )
        self.staff_user = User.objects.create_user(
            TEST_STAFF_USER_EMAIL, TEST_USER_PASSWORD, is_staff=True
        )

    def test_delete_requires_login(self):
        client = Client()
        url = reverse(
            "shifter_auth:user-delete", kwargs={"pk": self.regular_user.pk}
        )
        response = client.post(url)
        self.assertEqual(response.status_code, 302)

    def test_delete_requires_staff(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_auth:user-delete", kwargs={"pk": self.regular_user.pk}
        )
        response = client.post(url)
        self.assertEqual(response.status_code, 403)

    def test_delete_user(self):
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_auth:user-delete", kwargs={"pk": self.regular_user.pk}
        )
        response = client.post(url)
        self.assertEqual(response.status_code, 302)
        User = get_user_model()
        self.assertFalse(User.objects.filter(pk=self.regular_user.pk).exists())

    def test_cannot_delete_self(self):
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_auth:user-delete", kwargs={"pk": self.staff_user.pk}
        )
        response = client.post(url)
        self.assertEqual(response.status_code, 302)
        User = get_user_model()
        self.assertTrue(User.objects.filter(pk=self.staff_user.pk).exists())

    def test_get_not_allowed(self):
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_auth:user-delete", kwargs={"pk": self.regular_user.pk}
        )
        response = client.get(url)
        self.assertEqual(response.status_code, 405)

    @override_settings(MEDIA_ROOT="/tmp/test_media")
    def test_delete_user_expires_files(self):
        """Test that deleting a user sets their files to expired."""
        # Create a file for the regular user
        file_content = SimpleUploadedFile(
            "test_file.txt", b"Test content", content_type="text/plain"
        )
        future_expiry = timezone.now() + timezone.timedelta(days=7)
        file_upload = FileUpload.objects.create(
            owner=self.regular_user,
            filename="test_file.txt",
            upload_datetime=timezone.now(),
            expiry_datetime=future_expiry,
            file_content=file_content,
        )

        # Verify file is not expired
        self.assertFalse(file_upload.is_expired())

        # Delete the user
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_auth:user-delete", kwargs={"pk": self.regular_user.pk}
        )
        client.post(url)

        # Refresh file from database
        file_upload.refresh_from_db()

        # Verify file is now expired
        self.assertTrue(file_upload.is_expired())
        self.assertLessEqual(file_upload.expiry_datetime, timezone.now())

    @override_settings(MEDIA_ROOT="/tmp/test_media")
    def test_deactivate_user_does_not_affect_files(self):
        """Test that deactivating a user does NOT affect their files."""
        # Create a file for the regular user
        file_content = SimpleUploadedFile(
            "test_file.txt", b"Test content", content_type="text/plain"
        )
        future_expiry = timezone.now() + timezone.timedelta(days=7)
        file_upload = FileUpload.objects.create(
            owner=self.regular_user,
            filename="test_file.txt",
            upload_datetime=timezone.now(),
            expiry_datetime=future_expiry,
            file_content=file_content,
        )

        # Verify file is not expired
        self.assertFalse(file_upload.is_expired())
        original_expiry = file_upload.expiry_datetime

        # Deactivate the user
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        url = reverse(
            "shifter_auth:user-detail", kwargs={"pk": self.regular_user.pk}
        )
        client.post(
            url,
            {
                "email": TEST_USER_EMAIL,
                "is_staff": False,
                "is_active": False,  # Deactivate user
            },
        )

        # Refresh file from database
        file_upload.refresh_from_db()

        # Verify file is still NOT expired and expiry hasn't changed
        self.assertFalse(file_upload.is_expired())
        self.assertEqual(file_upload.expiry_datetime, original_expiry)


class UserResetPasswordViewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.regular_user = User.objects.create_user(
            TEST_USER_EMAIL, TEST_USER_PASSWORD
        )
        self.staff_user = User.objects.create_user(
            TEST_STAFF_USER_EMAIL, TEST_USER_PASSWORD, is_staff=True
        )

    def test_reset_requires_login(self):
        client = Client()
        response = client.post(
            reverse(
                "shifter_auth:user-reset-password",
                kwargs={"pk": self.regular_user.pk},
            )
        )
        self.assertEqual(response.status_code, 302)

    def test_reset_requires_staff(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.post(
            reverse(
                "shifter_auth:user-reset-password",
                kwargs={"pk": self.regular_user.pk},
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_reset_password(self):
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.post(
            reverse(
                "shifter_auth:user-reset-password",
                kwargs={"pk": self.regular_user.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("new_password", response.context)

        # Verify user must change password on login
        self.regular_user.refresh_from_db()
        self.assertTrue(self.regular_user.change_password_on_login)

        # Verify old password no longer works
        client2 = Client()
        self.assertFalse(
            client2.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        )

        # Verify new password works
        new_password = response.context["new_password"]
        self.assertTrue(
            client2.login(email=TEST_USER_EMAIL, password=new_password)
        )

    def test_get_not_allowed(self):
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(
            reverse(
                "shifter_auth:user-reset-password",
                kwargs={"pk": self.regular_user.pk},
            )
        )
        self.assertEqual(response.status_code, 405)
