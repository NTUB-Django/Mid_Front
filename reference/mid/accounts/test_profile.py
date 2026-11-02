from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from .models import User


class ProfileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="studenta", email="student-a@example.com", password="Password-Example-1001")
        cls.viewer = User.objects.create_user(username="studentb", email="student-b@example.com", password="Password-Example-1002")

    def test_profile_changes_are_private_until_explicitly_published(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("accounts:profile"), {"form_kind": "profile", "display_name": "新姓名", "student_class": "", "profile_public": "on"})
        self.assertEqual(response.status_code, 302)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.display_name, "新姓名")
        self.assertTrue(self.owner.profile_public)
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(reverse("accounts:member_profile", args=[self.owner.pk])).status_code, 200)
        self.owner.profile_public = False
        self.owner.save(update_fields=["profile_public"])
        self.assertEqual(self.client.get(reverse("accounts:member_profile", args=[self.owner.pk])).status_code, 404)

    def test_avatar_upload_respects_profile_visibility(self):
        picture = BytesIO()
        Image.new("RGB", (16, 16), "red").save(picture, format="PNG")
        picture.seek(0)
        with TemporaryDirectory() as folder, override_settings(MEDIA_ROOT=folder):
            self.client.force_login(self.owner)
            uploaded = SimpleUploadedFile("avatar.png", picture.read(), content_type="image/png")
            response = self.client.post(reverse("accounts:profile"), {"form_kind": "profile", "display_name": "頭像", "avatar": uploaded})
            self.assertEqual(response.status_code, 302)
            self.owner.refresh_from_db()
            self.assertTrue(self.owner.avatar.name.startswith("avatars/"))
            image_response = self.client.get(reverse("accounts:avatar", args=[self.owner.pk]))
            self.assertEqual(image_response.status_code, 200)
            image_response.close()
            self.client.force_login(self.viewer)
            self.assertEqual(self.client.get(reverse("accounts:avatar", args=[self.owner.pk])).status_code, 404)
