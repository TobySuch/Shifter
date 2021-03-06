from os import path

from django.test import TestCase

CSS_FILE_PATH = "/home/app/web/static/css/dist/styles.css"


class TestCssGeneration(TestCase):
    def test_css_generation(self):
        self.assertTrue(path.exists(CSS_FILE_PATH))
        self.assertGreater(path.getsize(CSS_FILE_PATH), 0)
