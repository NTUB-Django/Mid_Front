from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.auth.views import LogoutView
from django.db import models
from django.db import IntegrityError, transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
import secrets

from .decorators import admin_role_required, student_role_required
from .forms import AccountEmailForm, CaptchaAuthenticationForm, StudentProfileForm, StudentRegisterForm
from .models import User


class StudentLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = CaptchaAuthenticationForm

    def form_valid(self, form):
        if not form.get_user().is_student_role:
            form.add_error(None, "請使用對應身分的登入入口。")
            return self.form_invalid(form)
        response = super().form_valid(form)
        self.request.session.set_expiry(60 * 60 * 24 * 14 if self.request.POST.get("remember_me") else 0)
        messages.success(self.request, "登入成功，歡迎回來。")
        return response


class StudentLogoutView(LogoutView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.success(request, "已安全登出學生端。")
        return response


def register(request):
    if request.user.is_authenticated:
        return redirect("courses:home")
    token = request.session.get("register_token")
    if not token:
        token = secrets.token_urlsafe(24)
        request.session["register_token"] = token
    form = StudentRegisterForm(request.POST or None)
    if request.method == "POST" and not secrets.compare_digest(str(request.POST.get("register_token", "")), token):
        form.add_error(None, "這份註冊表單已送出或已失效，請重新整理後再試。")
        return render(request, "accounts/register.html", {"form": form, "register_token": token}, status=400)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
        except IntegrityError:
            form.add_error(None, "帳號或 Email 已被使用，請重新輸入。")
            return render(request, "accounts/register.html", {"form": form, "register_token": token}, status=400)
        request.session.pop("register_token", None)
        login(request, user)
        messages.success(request, "註冊成功，歡迎加入個人課表系統！")
        return redirect("courses:home")
    return render(request, "accounts/register.html", {"form": form, "register_token": token}, status=400 if request.method == "POST" else 200)


@never_cache
@login_required
def profile(request):
    email_post = request.method == "POST" and request.POST.get("form_kind", "email") == "email"
    profile_post = request.method == "POST" and request.POST.get("form_kind") == "profile" and request.user.is_student_role
    email_form = AccountEmailForm(request.POST if email_post else None, instance=request.user)
    student_form = StudentProfileForm(request.POST if profile_post else None, request.FILES if profile_post else None, instance=request.user) if request.user.is_student_role else None
    if profile_post and student_form.is_valid():
        student_form.save()
        messages.success(request, "個人資料已更新。")
        return redirect("accounts:profile")
    if email_post and email_form.is_valid():
        try:
            with transaction.atomic():
                email_form.save()
        except IntegrityError:
            email_form.add_error("email", "此 Email 已被使用。")
        else:
            messages.success(request, "登入 Email 已更新。")
            return redirect("school:profile" if request.session_scope == "school" else "accounts:profile")
    context = {
        "email_form": email_form,
        "student_form": student_form,
        "active_tab": "profile",
        "total_selected": request.user.selections.filter(status="selected").count(),
        "total_customs": request.user.custom_schedules.count(),
        "pre_count": request.user.selections.filter(status="pre").count(),
        "rejected_count": request.user.selections.filter(status="rejected").count(),
    }
    return render(request, "accounts/profile.html", context, status=400 if request.method == "POST" else 200)


@never_cache
@login_required
@student_role_required
def member_profile(request, user_id):
    person = get_object_or_404(User, pk=user_id, role=User.Role.STUDENT, is_active=True)
    if person.pk == request.user.pk:
        return redirect("accounts:profile")
    if not person.profile_public:
        raise Http404
    return render(request, "accounts/member_profile.html", {"person": person, "active_tab": "connections"})


@never_cache
@login_required
@student_role_required
def avatar(request, user_id):
    person = get_object_or_404(User, pk=user_id, role=User.Role.STUDENT, is_active=True)
    if person.pk != request.user.pk and not person.profile_public:
        raise Http404
    if not person.avatar:
        raise Http404
    response = FileResponse(person.avatar.open("rb"))
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
@admin_role_required
def manage_roles(request):
    pass
    if request.method == "POST":
        user_id = request.POST.get("user_id")
        new_role = request.POST.get("role")
        target_user = get_object_or_404(User, pk=user_id)
        if target_user == request.user and new_role != User.Role.ADMIN:
            messages.warning(request, "無法降級自己的最高管理員身分！")
        elif new_role in User.Role.values:
            target_user.role = new_role
            if new_role == User.Role.ADMIN:
                target_user.is_staff = True
                target_user.is_superuser = True
            elif new_role == User.Role.SCHOOL:
                target_user.is_staff = True
                target_user.is_superuser = False
            else:
                target_user.is_staff = False
                target_user.is_superuser = False
            target_user.save()
            messages.success(request, f"已將「{target_user.username}」的身分變更為「{target_user.get_role_display()}」！")
        return redirect("accounts:manage_roles")

    q = request.GET.get("q", "").strip()
    users_qs = User.objects.select_related("student_class").order_by("role", "username")
    if q:
        users_qs = users_qs.filter(models.Q(username__icontains=q) | models.Q(display_name__icontains=q))

    context = {
        "active_tab": "manage_roles",
        "users": users_qs,
        "roles": User.Role.choices,
        "q": q,
    }
    return render(request, "accounts/manage_roles.html", context)
