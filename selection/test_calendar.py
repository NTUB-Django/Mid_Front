from datetime import date, datetime, time

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Friendship, User
from courses.models import Course, Offering, OfferingSlot
from .models import AcademicTerm, PersonalEvent, Selection
from .privacy import visible_personal_events
from .services import get_timetable_stats


class CalendarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="s100001", email="student1@example.com", password="Example-Password-1001")
        cls.other = User.objects.create_user(username="s100002", email="student2@example.com", password="Example-Password-1002")

    def test_date_event_create_edit_delete_and_calendar_views(self):
        self.client.force_login(self.user)
        data = {
            "title": "小組報告", "starts_at_0": "2026-10-29", "starts_at_1": "13:30",
            "ends_at_0": "2026-10-29", "ends_at_1": "15:00", "location": "圖書館",
            "color": "red", "visibility": "private",
        }
        self.assertEqual(self.client.post(reverse("selection:event_new"), data).status_code, 302)
        event = PersonalEvent.objects.get(user=self.user)
        self.assertEqual(event.color, "red")
        for mode in ["day", "week", "month", "list"]:
            response = self.client.get(reverse("selection:calendar"), {"view": mode, "date": "2026-10-29"})
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "小組報告")
        data["title"] = "修改後報告"
        self.assertEqual(self.client.post(reverse("selection:event_edit", args=[event.pk]), data).status_code, 302)
        event.refresh_from_db()
        self.assertEqual(event.title, "修改後報告")
        self.assertEqual(self.client.post(reverse("selection:event_delete", args=[event.pk])).status_code, 302)
        self.assertFalse(PersonalEvent.objects.filter(pk=event.pk).exists())

    def test_private_events_and_owner_only_changes(self):
        event = PersonalEvent.objects.create(
            user=self.user, title="私人約會",
            starts_at=timezone.make_aware(datetime(2026, 10, 29, 9)),
            ends_at=timezone.make_aware(datetime(2026, 10, 29, 10)),
        )
        self.assertEqual(visible_personal_events(self.user, self.other).count(), 0)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("selection:event_edit", args=[event.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("selection:event_delete", args=[event.pk])).status_code, 404)
        low, high = sorted([self.user, self.other], key=lambda person: person.pk)
        Friendship.objects.create(user_low=low, user_high=high, requested_by=low, accepted=True)
        event.visibility = PersonalEvent.Visibility.FRIENDS
        event.save(update_fields=["visibility"])
        self.assertEqual(visible_personal_events(self.user, self.other).count(), 1)

    def test_semester_periods_follow_calendar_dates(self):
        course = Course.objects.create(code="C100", name="課堂")
        offering = Offering.objects.create(course=course, serial="01")
        OfferingSlot.objects.create(offering=offering, weekday=4, period="第一節", start=time(8, 10), end=time(9))
        Selection.objects.create(user=self.user, offering=offering)
        term = AcademicTerm.objects.get(is_current=True)
        expected = sum(1 for offset in range((term.ends_on - term.starts_on).days + 1) if ((day := date.fromordinal(term.starts_on.toordinal() + offset)).isoweekday() == 4 and day.isoformat() not in term.excluded_dates))
        stats = get_timetable_stats(self.user)
        self.assertEqual(stats["semester_periods"], expected)
        self.assertEqual(stats["total_weekly_periods"], 1)
