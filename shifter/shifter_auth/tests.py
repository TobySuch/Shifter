from django.test import TestCase, Client
from django.contrib.auth import get_user_model, get_user
from django.urls import reverse

TEST_USER_EMAIL = "iama@test.com"
TEST_USER_PASSWORD = "mytemporarypassword"


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
