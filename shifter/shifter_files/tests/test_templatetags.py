from django.test import TestCase

from shifter_files.templatetags.pretty_file_size import pretty_file_size

kilobyte = 1024
megabyte = kilobyte * 1024
gigabyte = megabyte * 1024
terabyte = gigabyte * 1024
petabyte = terabyte * 1024


class PrettyFileSizeTest(TestCase):
    def test_bytes(self):
        self.assertEqual(pretty_file_size(1), "1B")
        self.assertEqual(pretty_file_size(1023), "1023B")

    def test_kilobytes(self):
        self.assertEqual(pretty_file_size(kilobyte), "1KB")
        self.assertEqual(pretty_file_size(megabyte - 1), "1023KB")

    def test_megabytes(self):
        self.assertEqual(pretty_file_size(megabyte), "1MB")
        self.assertEqual(pretty_file_size(gigabyte - 1), "1023MB")

    def test_gigabytes(self):
        self.assertEqual(pretty_file_size(gigabyte), "1GB")
        self.assertEqual(pretty_file_size(terabyte - 1),
                         "1023GB")

    def test_terabytes(self):
        self.assertEqual(pretty_file_size(terabyte), "1TB")
        self.assertEqual(pretty_file_size(petabyte - 1), "1023TB")
        self.assertEqual(pretty_file_size(petabyte), "1024TB")
