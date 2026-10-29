from captcha.fields import CaptchaField
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import SharingGroup, User
from .social import member_groups


class CaptchaAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label="帳號或 Email", max_length=254)
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
            "placeholder": "輸入學號、帳號或 Email",
            "autocomplete": "username",
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
