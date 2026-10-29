
from datetime import time

from django.contrib.auth import authenticate
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from captcha.models import CaptchaStore

from courses.models import Department, EduType, StudentClass
from selection.models import CustomSchedule

from .forms import AccountEmailForm, StudentRegisterForm
from .models import Friendship, GroupMembership, SharingGroup, User
from .social import can_view_timetable


class SocialPrivacyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        edu = EduType.objects.create(code="4", name="四技")
        dept = Department.objects.create(edu=edu, code="401", name="資管")
        cls.school_class = StudentClass.objects.create(dept=dept, code="40110A", name="資管一甲")
        cls.owner = User.objects.create_user(username="owner", student_class=cls.school_class)
        cls.classmate = User.objects.create_user(username="classmate", student_class=cls.school_class)
        cls.friend = User.objects.create_user(username="friend")
        cls.stranger = User.objects.create_user(username="stranger")
        CustomSchedule.objects.create(user=cls.owner, title="private-event-marker", weekday=1, start=time(9), end=time(10), note="private-note-marker")

    def setUp(self):
        self.client.force_login(self.owner)

    def pair(self, accepted=False):
        low, high = sorted([self.owner.pk, self.friend.pk])
        return Friendship.objects.create(user_low_id=low, user_high_id=high, requested_by=self.owner, accepted=accepted)

    def test_default_classmates_only_and_null_class_is_not_same_class(self):
        self.assertTrue(can_view_timetable(self.classmate, self.owner))
        self.assertFalse(can_view_timetable(self.stranger, self.owner))
        self.assertFalse(can_view_timetable(self.stranger, self.friend))
        self.assertTrue(can_view_timetable(self.owner, self.owner))
        self.assertFalse(can_view_timetable(AnonymousUser(), self.owner))

    def test_direct_url_blocks_private_data_and_revocation(self):
        url = reverse("selection:user_timetable", args=[self.owner.pk])
        self.client.force_login(self.classmate)
        allowed = self.client.get(url)
        self.assertContains(allowed, "private-event-marker")
        self.assertIn("no-store", allowed.headers["Cache-Control"])
        self.owner.share_with_classmates = False
        self.owner.save()
        denied = self.client.get(url)
        self.assertEqual(denied.status_code, 403)
        self.assertNotContains(denied, "private-event-marker", status_code=403)
        self.assertNotContains(denied, "private-note-marker", status_code=403)

    def test_public_is_authenticated_students_only(self):
        self.owner.timetable_public = True
        self.owner.save()
        self.assertTrue(can_view_timetable(self.stranger, self.owner))
        staff = User.objects.create_user(username="school", role=User.Role.SCHOOL)
        self.assertFalse(can_view_timetable(staff, self.owner))
        self.stranger.is_active = False
        self.assertFalse(can_view_timetable(self.stranger, self.owner))

    def test_friend_request_requires_recipient_consent_and_single_pair(self):
        url = reverse("accounts:friend_request")
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url, {"username": self.friend.username})
        pair = Friendship.objects.get()
        self.client.post(url, {"username": self.friend.username})
        self.assertEqual(Friendship.objects.count(), 1)
        self.assertFalse(pair.accepted)
        accept = reverse("accounts:friend_action", args=[pair.pk, "accept"])
        self.assertEqual(self.client.post(accept).status_code, 400)
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.post(accept).status_code, 404)
        self.client.force_login(self.friend)
        self.client.post(url, {"username": self.owner.username})
        self.assertEqual(Friendship.objects.count(), 1)
        self.client.post(accept)
        pair.refresh_from_db()
        self.assertTrue(pair.accepted)

    def test_pending_friends_cannot_view_and_removal_revokes(self):
        self.owner.share_with_friends = True
        self.owner.save()
        pair = self.pair()
        self.assertFalse(can_view_timetable(self.friend, self.owner))
        pair.accepted = True
        pair.save()
        self.assertTrue(can_view_timetable(self.friend, self.owner))
        self.client.post(reverse("accounts:friend_action", args=[pair.pk, "remove"]))
        self.assertFalse(can_view_timetable(self.friend, self.owner))

    def test_self_and_nonstudent_friend_requests_rejected(self):
        url = reverse("accounts:friend_request")
        self.assertEqual(self.client.post(url, {"username": self.owner.username}).status_code, 400)
        staff = User.objects.create_user(username="staff", role=User.Role.SCHOOL)
        self.assertEqual(self.client.post(url, {"username": staff.username}).status_code, 404)
        self.assertEqual(Friendship.objects.count(), 0)

    def test_privacy_form_rejects_foreign_or_pending_group(self):
        group = SharingGroup.objects.create(owner=self.stranger, name="foreign")
        GroupMembership.objects.create(group=group, user=self.owner)
        response = self.client.post(reverse("accounts:privacy"), {"timetable_shared_groups": [group.pk]})
        self.assertEqual(response.status_code, 400)
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.share_with_classmates)
        self.assertFalse(self.owner.timetable_shared_groups.exists())

    def test_privacy_save_can_disable_all_and_is_not_get(self):
        url = reverse("accounts:privacy")
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url, {}).status_code, 302)
        self.owner.refresh_from_db()
        self.assertFalse(can_view_timetable(self.classmate, self.owner))

    def test_group_invitation_acceptance_and_leave_revoke_both_directions(self):
        self.pair(accepted=True)
        self.client.post(reverse("accounts:group_create"), {"name": "讀書小組"})
        group = SharingGroup.objects.get()
        invite = reverse("accounts:group_invite", args=[group.pk])
        self.assertEqual(self.client.post(invite, {"username": self.stranger.username}).status_code, 404)
        self.client.post(invite, {"username": self.friend.username})
        membership = GroupMembership.objects.get()
        self.owner.timetable_shared_groups.add(group)
        self.assertFalse(can_view_timetable(self.friend, self.owner))
        accept = reverse("accounts:membership_action", args=[membership.pk, "accept"])
        self.assertEqual(self.client.post(accept).status_code, 400)
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.post(accept).status_code, 400)
        self.client.force_login(self.friend)
        self.client.post(accept)
        self.assertTrue(can_view_timetable(self.friend, self.owner))
        self.assertFalse(can_view_timetable(self.owner, self.friend))
        self.friend.timetable_shared_groups.add(group)
        self.assertTrue(can_view_timetable(self.owner, self.friend))
        self.client.post(reverse("accounts:membership_action", args=[membership.pk, "remove"]))
        self.assertFalse(can_view_timetable(self.friend, self.owner))
        self.assertFalse(can_view_timetable(self.owner, self.friend))
        self.assertFalse(self.friend.timetable_shared_groups.exists())

    def test_group_ownership_and_deleted_group_revoke(self):
        group = SharingGroup.objects.create(owner=self.owner, name="private group")
        membership = GroupMembership.objects.create(group=group, user=self.friend, accepted=True)
        self.owner.timetable_shared_groups.add(group)
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.post(reverse("accounts:group_delete", args=[group.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("accounts:group_invite", args=[group.pk]), {"username": self.friend.username}).status_code, 404)
        self.assertEqual(self.client.post(reverse("accounts:membership_action", args=[membership.pk, "remove"])).status_code, 400)
        self.client.force_login(self.owner)
        self.client.post(reverse("accounts:group_delete", args=[group.pk]))
        self.assertFalse(can_view_timetable(self.friend, self.owner))
        self.assertFalse(self.owner.timetable_shared_groups.exists())

    def test_stale_group_grant_does_not_authorize_former_member(self):
        group = SharingGroup.objects.create(owner=self.stranger, name="stale group")
        GroupMembership.objects.create(group=group, user=self.friend, accepted=True)
        self.owner.timetable_shared_groups.add(group)
        self.assertFalse(can_view_timetable(self.friend, self.owner))

    def test_connections_shows_real_friends_private_indicator_and_pending_groups(self):
        self.classmate.share_with_classmates = False
        self.classmate.save()
        group = SharingGroup.objects.create(owner=self.friend, name="invited group")
        GroupMembership.objects.create(group=group, user=self.owner)
        response = self.client.get(reverse("accounts:connections"))
        self.assertContains(response, "尚未分享給你")
        self.assertContains(response, "invited group")
        self.assertEqual(len(response.context["friends"]), 0)
        self.assertIn("no-store", response.headers["Cache-Control"])
        response = self.client.get(reverse("selection:timetable"))
        self.assertEqual(len(response.context["other_friends"]), 0)

    def test_csrf_required_for_social_mutation(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(reverse("accounts:friend_request"), {"username": self.friend.username}).status_code, 403)
        self.assertFalse(Friendship.objects.exists())


class EmailLoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="email-student", email="student@example.com", password="Str0ng-planner-password")

    def test_login_by_email_case_insensitive(self):
        for identifier in ["student@example.com", "STUDENT@EXAMPLE.COM"]:
            self.assertEqual(authenticate(username=identifier, password="Str0ng-planner-password"), self.user)
        self.assertIsNone(authenticate(username="email-student", password="Str0ng-planner-password"))
        self.assertIsNone(authenticate(username="student@example.com", password="wrong"))

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        self.assertIsNone(authenticate(username=self.user.email, password="Str0ng-planner-password"))

    def test_username_cannot_be_used_instead_of_email(self):
        User.objects.create_user(username="student@example.com", password="Other-planner-password")
        self.assertEqual(authenticate(username="student@example.com", password="Str0ng-planner-password"), self.user)
        self.assertIsNone(authenticate(username="student@example.com", password="Other-planner-password"))

    def test_duplicate_email_rejected_by_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(username="duplicate", email="STUDENT@EXAMPLE.COM")

    def test_register_requires_unique_email_and_preserves_values(self):
        data = {"username": "new-student", "display_name": "新同學", "email": "STUDENT@EXAMPLE.COM", "password1": "Different-planner-password", "password2": "Different-planner-password"}
        self.assertFalse(StudentRegisterForm(data).is_valid())
        data["email"] = "NEW@example.com"
        form = StudentRegisterForm(data)
        self.assertTrue(form.is_valid(), form.errors)
        new_user = form.save()
        self.assertEqual(new_user.email, "new@example.com")
        self.assertEqual(authenticate(username="NEW@EXAMPLE.COM", password=data["password1"]), new_user)

    def test_email_change_needs_password_and_cannot_take_other_email(self):
        self.client.force_login(self.user)
        url = reverse("accounts:profile")
        response = self.client.post(url, {"email": "changed@example.com", "current_password": "wrong"})
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "student@example.com")
        response = self.client.post(url, {"email": "changed@example.com", "current_password": "Str0ng-planner-password"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(authenticate(username="changed@example.com", password="Str0ng-planner-password").pk, self.user.pk)
        self.assertIsNone(authenticate(username="student@example.com", password="Str0ng-planner-password"))
        other = User.objects.create_user(username="other", email="other@example.com")
        self.assertFalse(AccountEmailForm({"email": other.email, "current_password": "Str0ng-planner-password"}, instance=self.user).is_valid())

    def test_login_and_register_pages_show_email_fields(self):
        self.assertContains(self.client.get(reverse("accounts:login")), "Email")
        self.assertContains(self.client.get(reverse("accounts:register")), 'name="email"')

    def test_email_login_form_creates_session_with_valid_generated_challenge(self):
        key = CaptchaStore.generate_key()
        answer = CaptchaStore.objects.get(hashkey=key).response
        response = self.client.post(reverse("accounts:login"), {"username": "STUDENT@EXAMPLE.COM", "password": "Str0ng-planner-password", "captcha_0": key, "captcha_1": answer})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)
