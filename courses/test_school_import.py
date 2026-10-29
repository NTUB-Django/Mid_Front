from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User


class SchoolImportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = User.objects.create_user(username="teacher1", email="teacher@example.com", role=User.Role.SCHOOL)
        cls.admin = User.objects.create_superuser(username="admin", role=User.Role.ADMIN)

    def login_school(self):
        client = Client()
        client.force_login(self.teacher)
        self.client.cookies["mid_school_session"] = client.cookies["mid_student_session"].value

    def test_preview_and_confirm_student_with_required_email(self):
        self.login_school()
        upload = SimpleUploadedFile(
            "students.csv",
            "學號,Email,姓名,初始密碼\ns456789,new@example.com,新同學,Safe-new-student-905\n".encode(),
            content_type="text/csv",
        )
        response = self.client.post(reverse("school:student_import"), {"file": upload})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "s456789")
        self.assertFalse(User.objects.filter(username="s456789").exists())
        token = response.context["token"]
        self.assertIsNotNone(token)
        response = self.client.post(reverse("school:student_import_confirm"), {"token": token})
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="s456789")
        self.assertEqual(user.email, "new@example.com")
        self.assertTrue(user.check_password("Safe-new-student-905"))
        self.client.post(reverse("school:student_import_confirm"), {"token": token})
        self.assertEqual(User.objects.filter(username="s456789").count(), 1)

    def test_import_cannot_change_admin_and_rejects_missing_email(self):
        self.login_school()
        upload = SimpleUploadedFile(
            "students.csv",
            "學號,Email,姓名,初始密碼\nadmin,admin@example.com,管理員,Safe-new-student-905\ns456789,,新同學,Safe-new-student-905\n".encode(),
            content_type="text/csv",
        )
        response = self.client.post(reverse("school:student_import"), {"file": upload})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("token", response.context)
        self.assertEqual(User.objects.get(pk=self.admin.pk).role, User.Role.ADMIN)
