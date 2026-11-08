from django.contrib.auth import get_user_model
from django.tasks import TaskResultStatus
from django.test import TestCase
from django.urls import reverse
from django_tasks_db.models import DBTaskResult

from shifter_files.tasks import calculate_file_hash

PASSWORD = "mytemporarypassword"


class PruneTaskResultsViewTest(TestCase):
    url = reverse("shifter_files:prune-task-results")

    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            "staff@test.com", PASSWORD, is_staff=True
        )
        self.user = User.objects.create_user("user@test.com", PASSWORD)
        for status in (TaskResultStatus.SUCCESSFUL, TaskResultStatus.READY):
            result = calculate_file_hash.enqueue(0)
            DBTaskResult.objects.filter(id=result.id).update(status=status)

    def test_staff_can_prune(self):
        self.client.login(email=self.staff.email, password=PASSWORD)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"success": True, "num_results_deleted": 1}
        )
        self.assertEqual(DBTaskResult.objects.count(), 1)

    def test_non_staff_forbidden(self):
        self.client.login(email=self.user.email, password=PASSWORD)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(DBTaskResult.objects.count(), 2)

    def test_get_not_allowed(self):
        self.client.login(email=self.staff.email, password=PASSWORD)

        self.assertEqual(self.client.get(self.url).status_code, 405)
