from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "學生端"
        SCHOOL = "school", "學校端(教務/行政)"
        ADMIN = "admin", "最高管理員(Admin)"

    role = models.CharField("角色", max_length=20, choices=Role.choices, default=Role.STUDENT)
    display_name = models.CharField("顯示名稱", max_length=60, blank=True)
    timetable_public = models.BooleanField("公開給所有登入學生", default=False)
    share_with_classmates = models.BooleanField("分享給同班同學", default=True)
    share_with_friends = models.BooleanField("分享給好友", default=False)
    timetable_shared_groups = models.ManyToManyField("SharingGroup", blank=True, related_name="sharing_users", verbose_name="分享課表的群組")
    student_class = models.ForeignKey(
        "courses.StudentClass",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="所屬班級",
        related_name="students",
    )

    class Meta:
        verbose_name = "帳號"
        verbose_name_plural = "帳號"
        constraints = [models.UniqueConstraint(Lower("email"), condition=~models.Q(email=""), name="unique_user_email_ci")]

    def __str__(self):
        return f"{self.username}（{self.get_role_display()}）"

    def save(self, *args, **kwargs):
        pass





        if self.role == self.Role.ADMIN:
            self.is_staff = True
            self.is_superuser = True
        elif self.role == self.Role.SCHOOL:
            self.is_staff = True
            self.is_superuser = False
        elif self.role == self.Role.STUDENT and not self.is_superuser:
            self.is_staff = False
            self.is_superuser = False
        super().save(*args, **kwargs)

    @property
    def is_admin_role(self) -> bool:
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_school_role(self) -> bool:
        return self.role == self.Role.SCHOOL

    @property
    def is_student_role(self) -> bool:
        return self.role == self.Role.STUDENT

    @property
    def can_manage_school(self) -> bool:
        return self.is_school_role or self.is_admin_role


class Friendship(models.Model):
    user_low = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friendships_low")
    user_high = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friendships_high")
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_friendships")
    accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user_low", "user_high"], name="unique_friend_pair"),
            models.CheckConstraint(condition=models.Q(user_low__lt=models.F("user_high")), name="ordered_friend_pair"),
            models.CheckConstraint(condition=models.Q(requested_by=models.F("user_low")) | models.Q(requested_by=models.F("user_high")), name="friend_request_from_pair"),
        ]

    def other_user(self, user):
        return self.user_high if user.pk == self.user_low_id else self.user_low


class SharingGroup(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owned_sharing_groups")
    name = models.CharField("群組名稱", max_length=60)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}（{self.owner.display_name or self.owner.username}）"


class GroupMembership(models.Model):
    group = models.ForeignKey(SharingGroup, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sharing_memberships")
    accepted = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["group", "user"], name="unique_group_member")]
