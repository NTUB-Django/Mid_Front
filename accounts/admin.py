from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm as BaseAdminUserCreationForm, UserChangeForm

from .forms import validate_login_email
from .models import User


def clean_admin_email(data, instance=None):
    username = data.get("username", instance.username if instance else "")
    role = data.get("role", instance.role if instance else User.Role.STUDENT)
    email = (data.get("email") or "").strip()
    if username == "admin" and role == User.Role.ADMIN:
        return email.lower()
    if not email:
        raise forms.ValidationError("除了最高管理員 admin，所有帳號都必須設定 Email。")
    return validate_login_email(forms.EmailField().clean(email), instance)


class AdminUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User

    def clean(self):
        data = super().clean()
        try:
            data["email"] = clean_admin_email(data, self.instance)
        except forms.ValidationError as error:
            self.add_error("email", error)
        return data


class AdminUserCreationForm(BaseAdminUserCreationForm):
    class Meta(BaseAdminUserCreationForm.Meta):
        model = User
        fields = ("username", "email", "role", "display_name", "student_class")

    def clean(self):
        data = super().clean()
        try:
            data["email"] = clean_admin_email(data)
        except forms.ValidationError as error:
            self.add_error("email", error)
        return data


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = AdminUserChangeForm
    add_form = AdminUserCreationForm
    list_display = ("username", "display_name", "role", "student_class", "is_staff", "is_superuser", "is_active", "date_joined")
    list_filter = ("role", "is_staff", "is_superuser", "is_active", "student_class")
    search_fields = ("username", "display_name", "email")
    ordering = ("-date_joined",)

    fieldsets = BaseUserAdmin.fieldsets + (
        ("系統權限與角色資訊", {"fields": ("role", "display_name", "student_class")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("系統權限與角色資訊", {"fields": ("email", "role", "display_name", "student_class")}),
    )

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser and obj:
            return ("is_superuser", "user_permissions", "last_login", "date_joined")
        return ()
