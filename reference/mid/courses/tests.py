import io
import json
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from accounts.models import User
from django.urls import reverse

from .models import Course, Department, EduType, Offering, OfferingSlot, StudentClass


class CourseBootstrapTests(TestCase):
    def test_initial_import_is_persistent_and_does_not_overwrite_existing_data(self):
        record = {
            'query_ok': True, 'edu_code': '4', 'edu_name': '四技',
            'dept_code': '401', 'dept_name': '資管', 'class_code': '401A', 'class_name': '一年甲班',
            'sessions': [{'課程代號': 'TEST101', '課程名稱': '資料庫', '序號': '1',
                          '教師': '測試老師', '星期': '一', '節次': '第一節',
                          '開始時間': '08:10', '結束時間': '09:00', '教室': 'A101'}],
        }
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'courses.jsonl'
            source.write_text(json.dumps(record), encoding='utf-8')
            call_command('import_courses', file=str(source), if_empty=True, stdout=io.StringIO())
            self.assertEqual(Course.objects.count(), 1)
            self.assertEqual(OfferingSlot.objects.count(), 1)
            self.assertEqual(StudentClass.objects.count(), 1)
            offering = Offering.objects.get()
            offering.capacity = 75
            offering.save(update_fields=['capacity'])
            source.unlink()
            call_command('import_courses', file=str(source), if_empty=True, stdout=io.StringIO())
            offering.refresh_from_db()
            self.assertEqual(offering.capacity, 75)
            self.assertEqual(Offering.objects.count(), 1)


class GradeFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.edu = EduType.objects.create(code="4", name="四技")
        cls.dept = Department.objects.create(edu=cls.edu, code="401", name="資管")
        cls.other_dept = Department.objects.create(edu=cls.edu, code="402", name="會計")
        cls.year_one = StudentClass.objects.create(dept=cls.dept, code="one", name="四技資管一年甲班")
        cls.year_two = StudentClass.objects.create(dept=cls.dept, code="two", name="四技資管二年甲班")
        cls.other_one = StudentClass.objects.create(dept=cls.other_dept, code="other", name="會計一年甲班")
        cls.student = User.objects.create_user(username="grade-user", role=User.Role.STUDENT)
        cls.match = Offering.objects.create(course=Course.objects.create(code="G1", name="一年課程"), serial="1")
        cls.match.classes.add(cls.year_one, cls.other_one)
        cls.mixed = Offering.objects.create(course=Course.objects.create(code="G2", name="跨班課程"), serial="1")
        cls.mixed.classes.add(cls.year_two, cls.other_one)

    def setUp(self):
        self.client.force_login(self.student)

    def test_grade_matches_class_year_not_education_number(self):
        for name, expected in [("四技資管一年甲班", 1), ("五專會計五年乙班", 5), ("資管二甲", 2), ("資管３年甲班", 3), ("四技通識核心必修", None)]:
            with self.subTest(name=name):
                self.assertEqual(StudentClass(name=name).grade, expected)

    def test_grade_and_department_must_match_same_class(self):
        response = self.client.get(reverse("courses:browse"), {"edu": self.edu.pk, "dept": self.dept.pk, "grade": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["page_obj"]), [self.match])
        self.assertContains(response, '<option value="1" selected>1 年級</option>', html=True)

    def test_grade_filter_does_not_duplicate_cross_class_offerings(self):
        response = self.client.get(reverse("courses:browse"), {"grade": "1"})
        self.assertEqual(response.context["page_obj"].paginator.count, 2)

    def test_invalid_grade_is_shown_as_form_error(self):
        response = self.client.get(reverse("courses:browse"), {"grade": "bogus"})
        self.assertIn("grade", response.context["form"].errors)

    def test_grade_is_preserved_in_pagination(self):
        for index in range(25):
            offering = Offering.objects.create(course=Course.objects.create(code=f"PAGE{index}", name="更多課程"), serial="1")
            offering.classes.add(self.year_one)
        response = self.client.get(reverse("courses:browse"), {"grade": "1", "page": "2"})
        self.assertIn("grade=1", response.context["query_string"])
        self.assertEqual(response.context["page_obj"].number, 2)
