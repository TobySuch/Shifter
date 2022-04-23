from django.test import TestCase, Client
from django.urls import reverse

TEST_USER_EMAIL = "iama@test.com"
TEST_USER_PASSWORD = "mytemporarypassword"


class IndexViewTest(TestCase):
    def test_force_authentication(self):
        client = Client()
        response = client.get(reverse("shifter_files:index"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(reverse("shifter_auth:login") in response.url)
