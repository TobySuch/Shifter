from os import path

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

CSS_FILE_PATH = "/home/app/web/static/css/dist/styles.css"
FLOWBITE_FILE_PATH = "/home/app/web/static/js/flowbite/flowbite.js"

TEST_USER_EMAIL = "iama@test.com"
TEST_STAFF_USER_EMAIL = "iamastaff@test.com"
TEST_USER_PASSWORD = "mytemporarypassword"


class TestCssGeneration(TestCase):
    def test_css_generation(self):
        self.assertTrue(path.exists(CSS_FILE_PATH))
        self.assertGreater(path.getsize(CSS_FILE_PATH), 0)

    def test_flowbite_exists(self):
        self.assertTrue(path.exists(FLOWBITE_FILE_PATH))
        self.assertGreater(path.getsize(FLOWBITE_FILE_PATH), 0)


class TestNavBar(TestCase):
    def setUp(self):
        User = get_user_model()
        user = User.objects.create_user(TEST_USER_EMAIL,
                                        TEST_USER_PASSWORD)
        user.save()
        staff_user = User.objects.create_user(TEST_STAFF_USER_EMAIL,
                                              TEST_USER_PASSWORD,
                                              is_staff=True)
        staff_user.save()

    def test_new_user_link_visibility(self):
        client = Client()
        client.login(email=TEST_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_files:index"))
        self.assertInHTML("Register New User",
                          response.content.decode(), count=0)

        client.logout()
        client.login(email=TEST_STAFF_USER_EMAIL, password=TEST_USER_PASSWORD)
        response = client.get(reverse("shifter_files:index"))
        self.assertInHTML("Register New User",
                          response.content.decode())
