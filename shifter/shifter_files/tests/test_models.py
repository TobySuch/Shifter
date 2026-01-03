import datetime
import hashlib
import pathlib
import tempfile
from shutil import rmtree

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from shifter_files.models import FileUpload

TEST_USER_EMAIL = "iama@test.com"
TEST_USER_PASSWORD = "mytemporarypassword"

TEST_FILE_NAME = "mytestfile.txt"
TEST_FILE_CONTENT = b"Hello, World!"


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class FileUploadModelTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            TEST_USER_EMAIL, TEST_USER_PASSWORD
        )

    def tearDown(self):
        rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def test_add_new_file(self):
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        current_datetime = timezone.now()
        expiry_datetime = current_datetime + datetime.timedelta(days=1)
        file_upload = FileUpload.objects.create(
            owner=self.user,
            file_content=test_file,
            upload_datetime=current_datetime,
            expiry_datetime=expiry_datetime,
            filename=TEST_FILE_NAME,
        )

        self.assertEqual(FileUpload.objects.count(), 1)
        file_upload = FileUpload.objects.first()
        self.assertEqual(file_upload.filename, TEST_FILE_NAME)
        self.assertEqual(file_upload.owner, self.user)
        self.assertAlmostEqual(
            file_upload.upload_datetime,
            current_datetime,
            delta=datetime.timedelta(minutes=1),
        )
        self.assertAlmostEqual(
            file_upload.expiry_datetime,
            expiry_datetime,
            delta=datetime.timedelta(minutes=1),
        )
        # Ensure file has been uploaded to the correct location
        path = pathlib.Path(settings.MEDIA_ROOT + "/uploads/" + TEST_FILE_NAME)
        self.assertTrue(path.is_file())

    def test_is_expired_false(self):
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        current_datetime = timezone.now()
        expiry_datetime = current_datetime + datetime.timedelta(days=1)
        file_upload = FileUpload.objects.create(
            owner=self.user,
            file_content=test_file,
            upload_datetime=current_datetime,
            expiry_datetime=expiry_datetime,
            filename=TEST_FILE_NAME,
        )

        self.assertFalse(file_upload.is_expired())

    def test_is_expired_true(self):
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        current_datetime = timezone.now()
        expiry_datetime = current_datetime - datetime.timedelta(days=1)
        file_upload = FileUpload.objects.create(
            owner=self.user,
            file_content=test_file,
            upload_datetime=current_datetime,
            expiry_datetime=expiry_datetime,
            filename=TEST_FILE_NAME,
        )

        self.assertTrue(file_upload.is_expired())

    def test_get_expired_files(self):
        expired_files = FileUpload.get_expired_files()
        self.assertEqual(expired_files.count(), 0)

        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        current_datetime = timezone.now()
        expiry_datetime = current_datetime - datetime.timedelta(days=1)
        file_upload = FileUpload.objects.create(
            owner=self.user,
            file_content=test_file,
            upload_datetime=current_datetime,
            expiry_datetime=expiry_datetime,
            filename=TEST_FILE_NAME,
        )

        expired_files = FileUpload.get_expired_files()
        self.assertEqual(expired_files.count(), 1)
        self.assertEqual(expired_files.first(), file_upload)

        file_upload2 = FileUpload.objects.create(
            owner=self.user,
            file_content=test_file,
            upload_datetime=current_datetime,
            expiry_datetime=expiry_datetime,
            filename=TEST_FILE_NAME,
        )

        expired_files = FileUpload.get_expired_files()
        self.assertEqual(expired_files.count(), 2)
        self.assertEqual(expired_files.last(), file_upload2)

    def test_delete_expired_files_empty(self):
        self.assertEqual(FileUpload.get_expired_files().count(), 0)
        num_files_deleted = FileUpload.delete_expired_files()
        self.assertEqual(num_files_deleted, 0)

    def test_delete_expired_files(self):
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        current_datetime = timezone.now()
        expiry_datetime = current_datetime - datetime.timedelta(days=1)

        for _ in range(2):
            FileUpload.objects.create(
                owner=self.user,
                file_content=test_file,
                upload_datetime=current_datetime,
                expiry_datetime=expiry_datetime,
                filename=TEST_FILE_NAME,
            )

        self.assertEqual(FileUpload.get_expired_files().count(), 2)
        num_files_deleted = FileUpload.delete_expired_files()
        self.assertEqual(num_files_deleted, 2)
        self.assertEqual(FileUpload.get_expired_files().count(), 0)

    def test_calculate_file_hash_returns_md5_hex(self):
        """Test calculate_file_hash returns 32-character MD5 hex."""
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        calculated_hash = FileUpload.calculate_file_hash(test_file)

        # Verify hash is 32 characters (MD5 hex digest length)
        self.assertEqual(len(calculated_hash), 32)
        # Verify it's a valid hex string
        self.assertTrue(all(c in "0123456789abcdef" for c in calculated_hash))

    def test_calculate_file_hash_consistent(self):
        """Test calculate_file_hash returns same hash for same content."""
        test_file1 = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        test_file2 = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)

        calculated_hash1 = FileUpload.calculate_file_hash(test_file1)
        calculated_hash2 = FileUpload.calculate_file_hash(test_file2)

        self.assertEqual(calculated_hash1, calculated_hash2)

    def test_calculate_file_hash_matches_expected(self):
        """Test calculate_file_hash returns correct MD5."""
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        calculated_hash = FileUpload.calculate_file_hash(test_file)

        # Calculate expected hash using hashlib directly
        expected_hash = hashlib.md5(TEST_FILE_CONTENT).hexdigest()

        self.assertEqual(calculated_hash, expected_hash)

    def test_calculate_file_hash_different_content(self):
        """Test that different content produces different hashes."""
        test_file1 = SimpleUploadedFile(
            TEST_FILE_NAME, b"First content"
        )
        test_file2 = SimpleUploadedFile(
            TEST_FILE_NAME, b"Second content"
        )

        hash1 = FileUpload.calculate_file_hash(test_file1)
        hash2 = FileUpload.calculate_file_hash(test_file2)

        self.assertNotEqual(hash1, hash2)

    def test_calculate_file_hash_large_file(self):
        """Test calculate_file_hash works with large files."""
        # Create a file larger than 8KB chunk size (use 10KB)
        large_content = b"A" * 10240
        test_file = SimpleUploadedFile("largefile.txt", large_content)

        calculated_hash = FileUpload.calculate_file_hash(test_file)
        expected_hash = hashlib.md5(large_content).hexdigest()

        self.assertEqual(calculated_hash, expected_hash)

    def test_file_upload_without_hash(self):
        """Test FileUpload can be created without hash."""
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        current_datetime = timezone.now()
        expiry_datetime = current_datetime + datetime.timedelta(days=1)
        file_upload = FileUpload.objects.create(
            owner=self.user,
            file_content=test_file,
            upload_datetime=current_datetime,
            expiry_datetime=expiry_datetime,
            filename=TEST_FILE_NAME,
        )

        # Hash should be None when not explicitly set
        self.assertIsNone(file_upload.file_hash)

    def test_file_upload_with_hash(self):
        """Test that FileUpload can be created with hash."""
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        current_datetime = timezone.now()
        expiry_datetime = current_datetime + datetime.timedelta(days=1)

        # Calculate hash
        file_hash = FileUpload.calculate_file_hash(test_file)

        file_upload = FileUpload.objects.create(
            owner=self.user,
            file_content=test_file,
            upload_datetime=current_datetime,
            expiry_datetime=expiry_datetime,
            filename=TEST_FILE_NAME,
            file_hash=file_hash,
        )

        # Verify hash was stored
        self.assertIsNotNone(file_upload.file_hash)
        self.assertEqual(len(file_upload.file_hash), 32)
        self.assertEqual(
            file_upload.file_hash, hashlib.md5(TEST_FILE_CONTENT).hexdigest()
        )

    def test_file_without_expiry_is_not_expired(self):
        """Test that files without expiry_datetime are never expired."""
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        file_upload = FileUpload.objects.create(
            owner=self.user,
            filename="no_expiry.txt",
            upload_datetime=timezone.now(),
            expiry_datetime=None,  # No expiry
            file_content=test_file,
        )
        self.assertFalse(file_upload.is_expired())

    def test_get_expired_files_excludes_null_expiry(self):
        """Test that get_expired_files excludes files without expiry."""
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        current_datetime = timezone.now()

        # Create file with NULL expiry
        FileUpload.objects.create(
            owner=self.user,
            filename="no_expiry.txt",
            upload_datetime=current_datetime,
            expiry_datetime=None,
            file_content=test_file,
        )

        # Create expired file
        FileUpload.objects.create(
            owner=self.user,
            filename="expired.txt",
            upload_datetime=current_datetime - datetime.timedelta(days=2),
            expiry_datetime=current_datetime - datetime.timedelta(days=1),
            file_content=test_file,
        )

        expired_files = FileUpload.get_expired_files()
        self.assertEqual(expired_files.count(), 1)
        self.assertEqual(expired_files.first().filename, "expired.txt")

    def test_get_non_expired_files_includes_null_expiry(self):
        """Test that get_non_expired_files includes files without expiry."""
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        current_datetime = timezone.now()

        # Create file with NULL expiry
        FileUpload.objects.create(
            owner=self.user,
            filename="no_expiry.txt",
            upload_datetime=current_datetime,
            expiry_datetime=None,
            file_content=test_file,
        )

        # Create non-expired file
        FileUpload.objects.create(
            owner=self.user,
            filename="future.txt",
            upload_datetime=current_datetime,
            expiry_datetime=current_datetime + datetime.timedelta(days=1),
            file_content=test_file,
        )

        # Create expired file
        FileUpload.objects.create(
            owner=self.user,
            filename="expired.txt",
            upload_datetime=current_datetime - datetime.timedelta(days=2),
            expiry_datetime=current_datetime - datetime.timedelta(days=1),
            file_content=test_file,
        )

        non_expired_files = FileUpload.get_non_expired_files()
        self.assertEqual(non_expired_files.count(), 2)
        filenames = [f.filename for f in non_expired_files]
        self.assertIn("no_expiry.txt", filenames)
        self.assertIn("future.txt", filenames)

    def test_delete_expired_files_preserves_null_expiry(self):
        """Test that cleanup doesn't delete files without expiry."""
        test_file = SimpleUploadedFile(TEST_FILE_NAME, TEST_FILE_CONTENT)
        current_datetime = timezone.now()

        # Create file with NULL expiry
        no_expiry = FileUpload.objects.create(
            owner=self.user,
            filename="no_expiry.txt",
            upload_datetime=current_datetime,
            expiry_datetime=None,
            file_content=test_file,
        )

        # Create expired file
        FileUpload.objects.create(
            owner=self.user,
            filename="expired.txt",
            upload_datetime=current_datetime - datetime.timedelta(days=2),
            expiry_datetime=current_datetime - datetime.timedelta(days=1),
            file_content=test_file,
        )

        num_deleted = FileUpload.delete_expired_files()
        self.assertEqual(num_deleted, 1)

        # File without expiry should still exist
        self.assertTrue(
            FileUpload.objects.filter(file_hex=no_expiry.file_hex).exists()
        )
