from django.test import TestCase

from shifter_files.templatetags.pretty_file_size import pretty_file_size

kilobyte = 1000
megabyte = kilobyte * 1000
gigabyte = megabyte * 1000
terabyte = gigabyte * 1000
petabyte = terabyte * 1000


class PrettyFileSizeTest(TestCase):
    def test_bytes(self):
        self.assertEqual(pretty_file_size(1), "1B")
        self.assertEqual(pretty_file_size(999), "999B")

    def test_kilobytes(self):
        self.assertEqual(pretty_file_size(kilobyte), "1KB")
        self.assertEqual(pretty_file_size(megabyte - 1), "999KB")

    def test_megabytes(self):
        self.assertEqual(pretty_file_size(megabyte), "1MB")
        self.assertEqual(pretty_file_size(gigabyte - 1), "999MB")

    def test_gigabytes(self):
        self.assertEqual(pretty_file_size(gigabyte), "1GB")
        self.assertEqual(pretty_file_size(terabyte - 1), "999GB")

    def test_terabytes(self):
        self.assertEqual(pretty_file_size(terabyte), "1TB")
        self.assertEqual(pretty_file_size(petabyte - 1), "999TB")
        self.assertEqual(pretty_file_size(petabyte), "1000TB")
