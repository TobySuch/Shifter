from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

TEST_USER_EMAIL = "iama@test.com"
TEST_USER_PASSWORD = "mytemporarypassword"


class IndexViewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        User.objects.create_user(TEST_USER_EMAIL, TEST_USER_PASSWORD)

    def test_force_authentication(self):
        client = Client()
        response = client.get(reverse("shifter_files:index"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(reverse("shifter_auth:login") in response.url)

    def test_authenticated_user_not_redirected(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_files:index"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue("<h1 class=\"title\">Upload File</h1>")
