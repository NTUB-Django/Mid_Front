from datetime import time
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import CustomSchedule
from .services import STANDARD_PERIODS, build_personal_timetable


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

    def test_school_pool_export_xls_grid_imports_course_teacher_room_and_times(self):
        self.client.force_login(self.student)
        html = """<p align='center'>個人課表</p><table>
        <tr><td>節次</td><td>一</td><td>二</td><td>三</td><td>四</td><td>五</td><td>六</td><td>日</td></tr>
        <tr><td>第二節<br>09:10<br>10:00</td><td></td><td></td><td></td><td>網站設計<br>林老師<br>電708</td><td></td><td></td><td></td></tr>
        <tr><td>第三節<br>10:10<br>11:00</td><td></td><td></td><td></td><td>網站設計<br>林老師<br>電708</td><td></td><td></td><td></td></tr>
        <tr><td>第五節<br>13:30<br>14:20</td><td>作業系統<br>陳老師<br>電703</td><td></td><td></td><td></td><td></td><td></td><td></td></tr>
        </table>"""
        upload = SimpleUploadedFile("PoolExport.xls", html.encode("utf-8"), content_type="application/vnd.ms-excel")
        response = self.client.post(reverse("selection:excel_import"), {"file": upload})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "林老師")
        self.assertContains(response, "電708")
        self.assertContains(response, "週四")
        rows = self.client.session["excel_import_preview"]["rows"]
        self.assertEqual(len(rows), 3)
        self.assertEqual((rows[0]["weekday"], rows[0]["start"], rows[0]["end"]), (4, "09:10", "10:00"))
        self.assertEqual((rows[0]["teacher"], rows[0]["location"], rows[0]["note"]), ("林老師", "電708", "林老師"))
        token = self.client.session["excel_import_preview"]["token"]
        self.assertEqual(self.client.post(reverse("selection:excel_confirm"), {"token": token, "skip_conflicts": "yes"}).status_code, 302)
        self.assertEqual(CustomSchedule.objects.filter(user=self.student, import_source="excel").count(), 3)
        self.assertEqual(CustomSchedule.objects.get(user=self.student, title="作業系統").location, "電703")
        page = self.client.get(reverse("selection:timetable"))
        self.assertEqual(page.status_code, 200)
        timetable = page.context["timetable"]
        self.assertEqual(timetable["periods"], STANDARD_PERIODS[:9])
        self.assertEqual(timetable["grid"][4][0][0]["name"], "作業系統")
        self.assertContains(page, '<span class="tt-period-name">第五節</span>', html=True)
        self.assertNotContains(page, '<span class="tt-period-name">13:30–14:20</span>', html=True)

    def test_existing_imports_share_standard_rows_without_reimport(self):
        for weekday, period in [(1, ""), (3, "13:30–14:20")]:
            CustomSchedule.objects.create(
                user=self.student, title="作業系統", weekday=weekday,
                period=period, start=time(13, 30), end=time(14, 20),
                import_source="excel",
            )
        for full_grid in (True, False):
            with self.subTest(full_grid=full_grid):
                timetable = build_personal_timetable(self.student, full_grid=full_grid)
                matches = [i for i, period in enumerate(timetable["periods"])
                           if period[1:] == (time(13, 30), time(14, 20))]
                self.assertEqual(len(matches), 1)
                index = matches[0]
                self.assertEqual(timetable["periods"][index][0], "第五節")
                self.assertEqual(timetable["grid"][index][0][0]["name"], "作業系統")
                self.assertEqual(timetable["grid"][index][2][0]["name"], "作業系統")
                self.assertEqual(timetable["total_items"], 2)
        self.assertEqual(CustomSchedule.objects.filter(user=self.student, period="").count(), 1)

    def test_nonstandard_intervals_with_same_label_remain_separate(self):
        for start, end in [(time(12), time(12, 30)), (time(12, 30), time(13))]:
            CustomSchedule.objects.create(
                user=self.student, title="午間行程", weekday=1,
                period="中午", start=start, end=end,
            )
        for full_grid in (True, False):
            with self.subTest(full_grid=full_grid):
                timetable = build_personal_timetable(self.student, full_grid=full_grid)
                rows = [(i, period) for i, period in enumerate(timetable["periods"])
                        if period[0] == "中午"]
                self.assertEqual(len(rows), 2)
                for index, period in rows:
                    items = timetable["grid"][index][0]
                    self.assertEqual(len(items), 1)
                    self.assertEqual((items[0]["start"], items[0]["end"]), period[1:])

    def test_same_school_grid_saved_as_xlsx_is_recognized(self):
        from openpyxl import Workbook

        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["節次", "一", "二", "三", "四", "五", "六", "日"])
        sheet.append(["第二節\n09:10\n10:00", None, None, None, "網站設計\n林老師\n電708"])
        buffer = BytesIO()
        workbook.save(buffer)
        workbook.close()
        self.client.force_login(self.student)
        upload = SimpleUploadedFile("PoolExport.xlsx", buffer.getvalue())
        response = self.client.post(reverse("selection:excel_import"), {"file": upload})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "林老師")
        rows = self.client.session["excel_import_preview"]["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["weekday"], rows[0]["location"]), (4, "電708"))
