from django.test import TestCase, Client
from django.contrib.auth import get_user_model, get_user
from django.urls import reverse

TEST_USER_EMAIL = "iama@test.com"
TEST_STAFF_USER_EMAIL = "iamastaff@test.com"
TEST_ADDITIONAL_USER_EMAIL = "iamalsoa@test.com"
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


class CreateNewUserViewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        user = User.objects.create_user(TEST_USER_EMAIL,
                                        TEST_USER_PASSWORD)
        user.save()
        staff_user = User.objects.create_user(TEST_STAFF_USER_EMAIL,
                                              TEST_USER_PASSWORD,
                                              is_staff=True)
        staff_user.save()

    def test_page_load_not_staff(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_auth:create-new-user"))
        self.assertEqual(response.status_code, 403)
        self.assertInHTML("You do not have access to create new users."
                          " Please ask an administrator for assistance.",
                          response.content.decode())

    def test_page_load(self):
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_auth:create-new-user"))
        self.assertEqual(response.status_code, 200)

    def test_create_new_user(self):
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.post(reverse("shifter_auth:create-new-user"), {
            "email": TEST_ADDITIONAL_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
            "confirm_password": TEST_USER_PASSWORD
        })
        self.assertEqual(response.status_code, 302)

        User = get_user_model()
        users = User.objects.filter(email=TEST_ADDITIONAL_USER_EMAIL)
        self.assertEqual(users.count(), 1)
        self.assertTrue(users[0].change_password_on_login)

    def test_new_user_already_exists(self):
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.post(reverse("shifter_auth:create-new-user"), {
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
            "confirm_password": TEST_USER_PASSWORD
        })
        self.assertEqual(response.status_code, 200)
        self.assertInHTML("Email already taken!", response.content.decode())

        User = get_user_model()
        self.assertEqual(User.objects.filter(email=TEST_USER_EMAIL).count(), 1)

    def test_new_user_passwords_dont_match(self):
        client = Client()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.post(reverse("shifter_auth:create-new-user"), {
            "email": TEST_ADDITIONAL_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
            "confirm_password": TEST_USER_PASSWORD + "_wrong"
        })
        self.assertEqual(response.status_code, 200)
        self.assertInHTML("Passwords do not match!", response.content.decode())

        User = get_user_model()
        self.assertEqual(User.objects.filter(
            email=TEST_ADDITIONAL_USER_EMAIL).count(), 0)

    def test_new_user_not_staff(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.post(reverse("shifter_auth:create-new-user"), {
            "email": TEST_ADDITIONAL_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
            "confirm_password": TEST_USER_PASSWORD
        })
        self.assertEqual(response.status_code, 403)

        User = get_user_model()
        self.assertEqual(User.objects.filter(
            email=TEST_ADDITIONAL_USER_EMAIL).count(), 0)
