from datetime import time
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User
from courses.models import Course, Department, EduType, Offering, OfferingSlot, StudentClass
from selection.models import CustomSchedule, Selection
from selection.services import (
    add_course_to_timetable,
    build_personal_timetable,
    check_conflicts,
    check_custom_conflict,
    get_timetable_stats,
    import_class_timetable,
    remove_course_from_timetable,
)


class PersonalTimetableTests(TestCase):
    def setUp(self):

        self.edu = EduType.objects.create(code="4", name="四技")
        self.dept = Department.objects.create(edu=self.edu, code="401", name="資訊管理系")
        self.student_class = StudentClass.objects.create(dept=self.dept, code="40110A", name="資管一甲")


        self.student = User.objects.create_user(
            username="test_student",
            email="test-student@example.com",
            password="password123",
            role=User.Role.STUDENT,
            display_name="測試同學",
            student_class=self.student_class,
        )


        self.course_a = Course.objects.create(code="CS101", name="程式設計(一)")
        self.offering_a = Offering.objects.create(course=self.course_a, serial="1", teacher="張老師", capacity=50)
        self.offering_a.classes.add(self.student_class)
        self.slot_a1 = OfferingSlot.objects.create(
            offering=self.offering_a,
            weekday=1,
            period="第一節",
            start=time(8, 10),
            end=time(9, 0),
            room="資301",
        )
        self.slot_a2 = OfferingSlot.objects.create(
            offering=self.offering_a,
            weekday=1,
            period="第二節",
            start=time(9, 10),
            end=time(10, 0),
            room="資301",
        )


        self.course_b = Course.objects.create(code="MATH101", name="微積分")
        self.offering_b = Offering.objects.create(course=self.course_b, serial="2", teacher="李老師", capacity=50)
        self.slot_b = OfferingSlot.objects.create(
            offering=self.offering_b,
            weekday=1,
            period="第二節",
            start=time(9, 10),
            end=time(10, 0),
            room="綜101",
        )


        self.course_c = Course.objects.create(code="ENG101", name="實用英文")
        self.offering_c = Offering.objects.create(course=self.course_c, serial="3", teacher="王老師", capacity=50)
        self.offering_c.classes.add(self.student_class)
        self.slot_c = OfferingSlot.objects.create(
            offering=self.offering_c,
            weekday=2,
            period="第三節",
            start=time(10, 10),
            end=time(11, 0),
            room="育201",
        )

    def test_empty_timetable_page_includes_mobile_agenda(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("selection:timetable"))
        self.assertEqual(response.status_code, 200)
        days = response.context["mobile_timetable_days"]
        self.assertEqual(len(days), 7)
        self.assertEqual(sum(day["isToday"] for day in days), 1)
        self.assertTrue(all(not day["events"] for day in days))

    def test_add_and_remove_course_from_timetable(self):
        pass
        code, msg = add_course_to_timetable(self.student, self.offering_a)
        self.assertEqual(code, "ok")
        self.assertTrue(Selection.objects.filter(user=self.student, offering=self.offering_a, status="selected").exists())


        code2, msg2 = add_course_to_timetable(self.student, self.offering_a)
        self.assertEqual(code2, "duplicate")


        deleted = remove_course_from_timetable(self.student, self.offering_a.id)
        self.assertTrue(deleted)
        self.assertFalse(Selection.objects.filter(user=self.student, offering=self.offering_a).exists())

    def test_course_conflict_detection(self):
        pass

        add_course_to_timetable(self.student, self.offering_a)


        conflicts = check_conflicts(self.offering_b, self.student)
        self.assertTrue(len(conflicts) > 0)

        code, msg = add_course_to_timetable(self.student, self.offering_b)
        self.assertEqual(code, "conflict")
        self.assertIn("衝堂", msg)

    def test_conflicting_course_returns_popup_notice_without_adding(self):
        add_course_to_timetable(self.student, self.offering_a)
        self.client.force_login(self.student)
        response = self.client.get(reverse("selection:course_add", args=[self.offering_b.pk]), follow=True)
        self.assertContains(response, 'data-schedule-conflict data-conflict-kind="blocked"')
        self.assertContains(response, 'id="schedule-conflict-dialog"')
        self.assertContains(response, "09:10–10:00")
        self.assertFalse(Selection.objects.filter(user=self.student, offering=self.offering_b).exists())

    def test_preselected_course_still_checks_conflict_before_promotion(self):
        add_course_to_timetable(self.student, self.offering_a)
        selection = Selection.objects.create(user=self.student, offering=self.offering_b, status=Selection.Status.PRE)
        code, _ = add_course_to_timetable(self.student, self.offering_b)
        self.assertEqual(code, "conflict")
        selection.refresh_from_db()
        self.assertEqual(selection.status, Selection.Status.PRE)

    def test_custom_overlap_popup_explains_schedule_was_saved(self):
        add_course_to_timetable(self.student, self.offering_a)
        self.client.force_login(self.student)
        response = self.client.post(reverse("selection:custom_schedule_add"), {"title": "重疊行程", "weekday": 1, "start": "08:30", "end": "09:30", "color": "blue"}, follow=True)
        self.assertContains(response, 'data-schedule-conflict data-conflict-kind="saved"')
        self.assertContains(response, "行程已儲存")
        self.assertTrue(self.student.custom_schedules.filter(title="重疊行程").exists())

    def test_class_import_popup_lists_skipped_conflicts(self):
        add_course_to_timetable(self.student, self.offering_b)
        self.client.force_login(self.student)
        response = self.client.post(reverse("selection:import_class"), {"student_class": self.student_class.pk}, follow=True)
        self.assertContains(response, 'data-schedule-conflict data-conflict-kind="import"')
        self.assertContains(response, "因衝堂未加入")
        self.assertFalse(self.student.selections.filter(offering=self.offering_a).exists())

    def test_custom_schedule_and_conflicts(self):
        pass

        custom = CustomSchedule.objects.create(
            user=self.student,
            title="系學會幹部會議",
            weekday=3,
            period="第五節",
            start=time(13, 30),
            end=time(14, 20),
            location="學生活動中心",
            color="blue",
        )
        self.assertEqual(self.student.custom_schedules.count(), 1)


        c_conflicts = check_custom_conflict(self.student, 3, time(13, 0), time(14, 0))
        self.assertTrue(len(c_conflicts) > 0)
        self.assertIn("系學會幹部會議", c_conflicts[0])


        custom.delete()
        self.assertEqual(self.student.custom_schedules.count(), 0)

    def test_import_class_timetable(self):
        pass

        res = import_class_timetable(self.student, self.student_class)
        self.assertEqual(res["added"], 2)
        self.assertEqual(Selection.objects.filter(user=self.student, status="selected").count(), 2)


        res2 = import_class_timetable(self.student, self.student_class)
        self.assertEqual(res2["added"], 0)
        self.assertEqual(res2["skipped"], 2)

    def test_build_personal_timetable_grid_and_stats(self):
        pass
        add_course_to_timetable(self.student, self.offering_a)
        CustomSchedule.objects.create(
            user=self.student,
            title="圖書館自修",
            weekday=4,
            period="第四節",
            start=time(11, 10),
            end=time(12, 0),
            location="圖書館 3F",
            color="green",
        )

        tt = build_personal_timetable(self.student, full_grid=True)
        self.assertIn("periods", tt)
        self.assertIn("grid", tt)
        self.assertEqual(tt["total_items"], 3)

        stats = get_timetable_stats(self.student)
        self.assertEqual(stats["total_courses"], 1)
        self.assertEqual(stats["total_customs"], 1)
        self.assertEqual(stats["total_weekly_periods"], 3)

    def test_views_response(self):
        pass
        self.client.force_login(self.student)


        resp = self.client.get(reverse("courses:home"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "今日總覽")


        resp = self.client.get(reverse("selection:timetable"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "115學年度 第1學期")


        resp = self.client.get(reverse("selection:timetable_print"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "國立臺北商業大學 — 個人每週課表")


        resp = self.client.post(reverse("selection:course_add", args=[self.offering_a.id]), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Selection.objects.filter(user=self.student, offering=self.offering_a).exists())


        resp = self.client.post(reverse("selection:course_remove", args=[self.offering_a.id]), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Selection.objects.filter(user=self.student, offering=self.offering_a).exists())

    def test_idor_protection_on_custom_schedule(self):
        pass
        other_student = User.objects.create_user(
            username="other_student",
            password="password456",
            role=User.Role.STUDENT,
        )
        other_custom = CustomSchedule.objects.create(
            user=other_student,
            title="他人機密行程",
            weekday=1,
            start=time(14, 0),
            end=time(15, 0),
        )

        self.client.force_login(self.student)
        resp = self.client.post(reverse("selection:custom_schedule_delete", args=[other_custom.id]))

        self.assertEqual(resp.status_code, 404)
        self.assertTrue(CustomSchedule.objects.filter(id=other_custom.id).exists())

    def test_update_course_preference(self):
        pass
        add_course_to_timetable(self.student, self.offering_a)
        self.client.force_login(self.student)

        resp = self.client.post(
            reverse("selection:course_update_pref", args=[self.offering_a.id]),
            {"color": "green", "notes": "期末大專案小組"},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        sel = Selection.objects.get(user=self.student, offering=self.offering_a)
        self.assertEqual(sel.color, "green")
        self.assertEqual(sel.notes, "期末大專案小組")

    def test_view_friend_timetable(self):
        pass
        friend = User.objects.create_user(
            username="friend_lin",
            password="password789",
            role=User.Role.STUDENT,
            display_name="林宇翔",
            student_class=self.student_class,
        )
        add_course_to_timetable(friend, self.offering_a)

        self.client.force_login(self.student)
        resp = self.client.get(reverse("selection:user_timetable", args=[friend.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "林宇翔 的課表")
        self.assertContains(resp, "程式設計(一)")

    def test_three_roles_and_permissions(self):
        pass
        school_staff = User.objects.create_user(
            username="school_staff",
            email="school-staff@example.com",
            password="staff_password",
            role=User.Role.SCHOOL,
            is_staff=True,
        )
        admin_user = User.objects.create_user(
            username="admin",
            password="admin_password",
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )


        school_client = Client()
        school_client.force_login(school_staff)
        self.client.cookies["mid_school_session"] = school_client.cookies["mid_student_session"].value
        resp_school = self.client.get(reverse("school:dashboard"))
        self.assertEqual(resp_school.status_code, 200)
        self.assertContains(resp_school, "學校端（教務處）管理中心")

        resp_class_tt = self.client.get(reverse("school:classes"))
        self.assertEqual(resp_class_tt.status_code, 200)


        resp_manage = self.client.get(reverse("accounts:manage_roles"))
        self.assertNotEqual(resp_manage.status_code, 200)


        admin_client = Client()
        admin_client.force_login(admin_user)
        self.client.cookies["mid_admin_session"] = admin_client.cookies["mid_student_session"].value
        resp_admin_backend = self.client.get(reverse("admin:index"))
        self.assertEqual(resp_admin_backend.status_code, 200)


        self.client.force_login(self.student)
        resp_student_blocked = self.client.get(reverse("accounts:manage_roles"))
        self.assertNotEqual(resp_student_blocked.status_code, 200)

    def test_role_security_and_sqlite_sync(self):
        pass
        u = User.objects.create(username="temp_role_user", role=User.Role.ADMIN)
        self.assertTrue(u.is_staff)
        self.assertTrue(u.is_superuser)

        u.role = User.Role.SCHOOL
        u.save()
        self.assertTrue(u.is_staff)
        self.assertFalse(u.is_superuser)

        u.role = User.Role.STUDENT
        u.save()
        self.assertFalse(u.is_staff)
        self.assertFalse(u.is_superuser)

    def test_login_page_renders_captcha(self):
        pass
        resp = self.client.get(reverse("accounts:login"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "圖片驗證碼")
        self.assertContains(resp, "captcha")
        self.assertContains(resp, "js/signin.js")

    def test_calendar_editor_creates_and_updates_a_weekly_event(self):
        self.client.force_login(self.student)
        values = {"title": "專題討論", "weekday": "3", "start": "13:00", "end": "14:30", "color": "green", "location": "圖書館", "note": "帶筆電"}
        response = self.client.post(reverse("selection:custom_schedule_add"), values)
        self.assertRedirects(response, reverse("selection:timetable"))
        item = CustomSchedule.objects.get(user=self.student)
        values.update(title="更新後的專題討論", end="15:00")
        response = self.client.post(reverse("selection:custom_schedule_update", args=[item.pk]), values, follow=True)
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.title, "更新後的專題討論")
        self.assertEqual(item.end, time(15, 0))
        self.assertNotContains(response, "與現有排程重疊")
        self.assertContains(response, f'data-edit-schedule="{item.pk}"')
        self.assertEqual(response.context["mobile_timetable_days"][2]["events"][0]["customId"], item.pk)

    def test_invalid_calendar_event_keeps_values_and_opens_editor(self):
        self.client.force_login(self.student)
        values = {"title": "不要遺失的行程", "weekday": "2", "start": "14:00", "end": "13:00", "color": "blue", "note": "保留備註"}
        response = self.client.post(reverse("selection:custom_schedule_add"), values)
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "不要遺失的行程", status_code=400)
        self.assertContains(response, "保留備註", status_code=400)
        self.assertTrue(response.context["editor_open"])
        self.assertFalse(CustomSchedule.objects.filter(user=self.student).exists())

    def test_calendar_update_and_delete_require_owner_and_post(self):
        owner = User.objects.create_user(username="event-owner", role=User.Role.STUDENT)
        item = CustomSchedule.objects.create(user=owner, title="私人活動", weekday=2, start=time(13), end=time(14))
        self.client.force_login(self.student)
        self.assertEqual(self.client.post(reverse("selection:custom_schedule_update", args=[item.pk]), {}).status_code, 404)
        self.assertEqual(self.client.get(reverse("selection:custom_schedule_add")).status_code, 405)
        self.assertEqual(self.client.get(reverse("selection:custom_schedule_update", args=[item.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse("selection:custom_schedule_delete", args=[item.pk])).status_code, 405)
        self.assertTrue(CustomSchedule.objects.filter(pk=item.pk).exists())

    def test_calendar_submission_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.student)
        self.assertEqual(client.post(reverse("selection:custom_schedule_add"), {}).status_code, 403)

    def test_friend_timetable_has_no_calendar_edit_controls(self):
        friend = User.objects.create_user(username="readonly-friend", role=User.Role.STUDENT, timetable_public=True)
        CustomSchedule.objects.create(user=friend, title="自習", weekday=1, start=time(13), end=time(14))
        self.client.force_login(self.student)
        response = self.client.get(reverse("selection:user_timetable", args=[friend.pk]))
        self.assertNotContains(response, "data-edit-schedule=")
        self.assertNotContains(response, 'class="tt-create-event"')


class PwaNavigationTests(TestCase):
    def test_manifest_covers_login_courses_profile_and_timetable(self):
        import json
        from urllib.parse import urljoin

        response = self.client.get(reverse("pwa_manifest"))
        manifest = json.loads(response.content)
        self.assertEqual(manifest["scope"], "/")
        self.assertEqual(manifest["display"], "standalone")
        self.assertEqual(manifest["id"], "/selection/timetable/")
        scope = urljoin("https://class2dj.nsir.uk/manifest.json", manifest["scope"])
        for route in ["accounts:login", "accounts:profile", "courses:browse", "selection:timetable", "selection:timetable_print"]:
            self.assertTrue(urljoin("https://class2dj.nsir.uk/", reverse(route)).startswith(scope))
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_worker_updates_without_shared_html_cache(self):
        response = self.client.get(reverse("service_worker"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertContains(response, "ntub-mid-")

    def test_print_page_has_pwa_metadata(self):
        user = User.objects.create_user(username="pwa-user", role=User.Role.STUDENT)
        self.client.force_login(user)
        response = self.client.get(reverse("selection:timetable_print"))
        self.assertContains(response, '<link rel="manifest" href="/manifest.json">', html=True)
