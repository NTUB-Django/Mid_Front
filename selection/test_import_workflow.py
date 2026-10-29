from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import CustomSchedule


class ExcelImportWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create_user(username="s123456", email="student@example.com")

    def test_excel_preview_confirm_and_batch_clear_preserves_personal_event(self):
        self.client.force_login(self.student)
        CustomSchedule.objects.create(user=self.student, title="讀書", weekday=2, start="14:00", end="15:00", color="red")
        upload = SimpleUploadedFile(
            "timetable.csv",
            "課程名稱,星期,開始時間,結束時間,教室\n程式設計,週一,08:10,10:00,301\n".encode(),
            content_type="text/csv",
        )
        response = self.client.post(reverse("selection:excel_import"), {"file": upload})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "程式設計")
        token = self.client.session["excel_import_preview"]["token"]
        self.client.post(reverse("selection:excel_confirm"), {"token": token, "skip_conflicts": "yes"})
        self.assertEqual(CustomSchedule.objects.filter(user=self.student, import_source="excel").count(), 1)
        page = self.client.get(reverse("selection:timetable"))
        self.assertContains(page, "批次刪除匯入")
        self.client.post(reverse("selection:clear_imported"))
        self.assertFalse(CustomSchedule.objects.filter(user=self.student, import_source="excel").exists())
        self.assertTrue(CustomSchedule.objects.filter(user=self.student, title="讀書", color="red").exists())
