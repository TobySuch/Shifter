from django.test import TestCase, Client
from django.contrib.auth import get_user_model, get_user
from django.urls import reverse

TEST_USER_EMAIL = "iama@test.com"
TEST_USER_PASSWORD = "mytemporarypassword"
TEST_USER_NEW_PASSWORD = "mynewpassword"


class IndexViewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        User.objects.create_user(TEST_USER_EMAIL, TEST_USER_PASSWORD)

    def test_logout_unauthenticated(self):
        client = Client()
        response = client.post(reverse("shifter_auth:logout"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url,
                         reverse("shifter_auth:login") + "?next=/auth/logout")

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
        self.assertEqual(response.url, reverse("shifter_auth:change-password"))

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
        response = client.get(reverse("shifter_auth:change-password"))
        self.assertEqual(response.status_code, 200)


class ChangePasswordViewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        user = User.objects.create_user(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        user.save()

    def test_page_load(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_auth:change-password"))
        self.assertEqual(response.status_code, 200)

    def test_successful_form_submit(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.post(reverse("shifter_auth:change-password"), {
            "new_password": TEST_USER_NEW_PASSWORD,
            "confirm_password": TEST_USER_NEW_PASSWORD
        })
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
        response = client.post(reverse("shifter_auth:change-password"), {
            "new_password": TEST_USER_NEW_PASSWORD,
            "confirm_password": TEST_USER_NEW_PASSWORD + "wrong"
        })
        self.assertEqual(response.status_code, 200)
        self.assertInHTML("Passwords do not match!", response.content.decode())
