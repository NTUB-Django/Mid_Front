from captcha.fields import CaptchaField
from django import forms
import re
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import GroupEvent, GroupMemo, GroupTask, SharingGroup, User
from .social import member_groups


class CaptchaAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label="Email（最高管理員可輸入 admin）", max_length=254)
    pass
    captcha = CaptchaField(
        label="安全驗證碼",
        error_messages={
            "invalid": "驗證碼輸入錯誤或已失效，請點擊驗證碼圖片刷新後重新輸入",
            "required": "請輸入圖片中的驗證碼",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "輸入 Email；最高管理員使用 admin",
            "autocomplete": "email",
            "autocapitalize": "none",
            "autofocus": "autofocus",
        })
        self.fields["password"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "請輸入密碼",
        })
        self.fields["captcha"].widget.attrs.update({
            "class": "form-control captcha-input",
            "placeholder": "請輸入右側驗證碼",
            "autocomplete": "off",
        })

    def clean_username(self):
        value = self.cleaned_data["username"].strip()
        if value != "admin":
            forms.EmailField().clean(value)
        return value


class StudentRegisterForm(UserCreationForm):
    display_name = forms.CharField(label="顯示名稱", max_length=60, required=False)
    email = forms.EmailField(label="Email", max_length=254)

    class Meta:
        model = User
        fields = ["username", "display_name", "email"]

    def clean_email(self):
        return validate_login_email(self.cleaned_data["email"])

    def clean_username(self):
        username = self.cleaned_data["username"]
        if not re.fullmatch(r"[A-Za-z0-9_-]{3,30}", username) or username.lower() == "admin":
            raise forms.ValidationError("學號須為 3–30 個英數字、底線或連字號，且不可使用 admin。")
        if User.objects.filter(email__iexact=username).exists():
            raise forms.ValidationError("此帳號無法使用，請選擇其他帳號。")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STUDENT
        user.display_name = self.cleaned_data.get("display_name", "")
        if commit:
            user.save()
        return user


def validate_login_email(value, user=None):
    email = value.strip().lower()
    others = User.objects.exclude(pk=user.pk) if user else User.objects.all()
    if others.filter(email__iexact=email).exists() or others.filter(username__iexact=email).exists():
        raise forms.ValidationError("此 Email 無法使用，請使用其他 Email。")
    return email


class AccountEmailForm(forms.ModelForm):
    email = forms.EmailField(label="登入 Email", max_length=254, widget=forms.EmailInput(attrs={"class": "input", "autocomplete": "email"}))
    current_password = forms.CharField(label="目前密碼", widget=forms.PasswordInput(attrs={"class": "input", "autocomplete": "current-password"}))

    class Meta:
        model = User
        fields = ["email"]

    def clean_email(self):
        return validate_login_email(self.cleaned_data["email"], self.instance)

    def clean_current_password(self):
        value = self.cleaned_data["current_password"]
        if not self.instance.check_password(value):
            raise forms.ValidationError("目前密碼不正確。")
        return value

    def save(self, commit=True):
        user = super().save(commit=False)
        if "email" in self.changed_data:
            user.email_verified_at = None
        if commit:
            user.save()
        return user


class TimetablePrivacyForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["timetable_public", "share_with_classmates", "share_with_friends", "timetable_shared_groups"]
        widgets = {"timetable_shared_groups": forms.CheckboxSelectMultiple()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["timetable_shared_groups"].queryset = member_groups(self.instance).select_related("owner").order_by("name", "pk")


class SharingGroupForm(forms.ModelForm):
    class Meta:
        model = SharingGroup
        fields = ["name"]
        widgets = {"name": forms.TextInput(attrs={"class": "input", "placeholder": "例如：期中讀書小組"})}


class GroupEventForm(forms.ModelForm):
    class Meta:
        model = GroupEvent
        fields = ["title", "starts_at", "ends_at", "location", "note", "color"]
        labels = {"title": "行程名稱", "starts_at": "開始時間", "ends_at": "結束時間", "location": "地點", "note": "備註", "color": "行程顏色"}
        widgets = {
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "input"}, format="%Y-%m-%dT%H:%M"),
            "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "input"}, format="%Y-%m-%dT%H:%M"),
            "title": forms.TextInput(attrs={"class": "input"}),
            "location": forms.TextInput(attrs={"class": "input"}),
            "note": forms.Textarea(attrs={"class": "input", "rows": 3}),
            "color": forms.Select(attrs={"class": "input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from selection.models import EVENT_COLORS
        self.fields["color"] = forms.ChoiceField(
            choices=[(key, value["label"]) for key, value in EVENT_COLORS.items()],
            initial=self.instance.color if self.instance.pk else "blue",
            widget=forms.Select(attrs={"class": "input"}),
        )

    def clean(self):
        data = super().clean()
        if data.get("starts_at") and data.get("ends_at") and data["starts_at"] >= data["ends_at"]:
            self.add_error("ends_at", "結束時間必須晚於開始時間。")
        return data


class GroupTaskForm(forms.ModelForm):
    class Meta:
        model = GroupTask
        fields = ["title", "due_at"]
        labels = {"title": "待辦事項", "due_at": "截止時間（選填）"}
        widgets = {
            "title": forms.TextInput(attrs={"class": "input", "placeholder": "例如：完成報告初稿"}),
            "due_at": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "input"}, format="%Y-%m-%dT%H:%M"),
        }


class GroupMemoForm(forms.ModelForm):
    class Meta:
        model = GroupMemo
        fields = ["title", "body"]
        labels = {"title": "備忘標題", "body": "備忘內容"}
        widgets = {
            "title": forms.TextInput(attrs={"class": "input", "placeholder": "例如：期末報告分工"}),
            "body": forms.Textarea(attrs={"class": "input", "rows": 6}),
        }
