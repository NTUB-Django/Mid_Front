from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db import models
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache

from .decorators import admin_role_required, student_role_required
from .forms import AccountEmailForm, CaptchaAuthenticationForm, StudentRegisterForm
from .models import User


class StudentLoginView(LoginView):
    pass
    template_name = "accounts/login.html"
    authentication_form = CaptchaAuthenticationForm

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.session.set_expiry(60 * 60 * 24 * 14 if self.request.POST.get("remember_me") else 0)
        return response


def register(request):
    if request.user.is_authenticated:
        return redirect("courses:home")
    form = StudentRegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
        except IntegrityError:
            form.add_error(None, "帳號或 Email 已被使用，請重新輸入。")
            return render(request, "accounts/register.html", {"form": form}, status=400)
        login(request, user)
        messages.success(request, "註冊成功，歡迎加入個人課表系統！")
        return redirect("courses:home")
    return render(request, "accounts/register.html", {"form": form})


@never_cache
@login_required
def profile(request):
    email_form = AccountEmailForm(request.POST if request.method == "POST" else None, instance=request.user)
    if request.method == "POST" and email_form.is_valid():
        try:
            with transaction.atomic():
                email_form.save()
        except IntegrityError:
            email_form.add_error("email", "此 Email 已被使用。")
        else:
            messages.success(request, "登入 Email 已更新，可使用 Email 或原帳號搭配密碼登入。")
            return redirect("accounts:profile")
    context = {
        "email_form": email_form,
        "active_tab": "profile",
        "total_selected": request.user.selections.filter(status="selected").count(),
        "total_customs": request.user.custom_schedules.count(),
        "pre_count": request.user.selections.filter(status="pre").count(),
        "rejected_count": request.user.selections.filter(status="rejected").count(),
    }
    return render(request, "accounts/profile.html", context, status=400 if request.method == "POST" else 200)


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


@login_required
def switch_role(request, role):
    pass
    if not (request.user.is_superuser or request.user.is_admin_role or request.user.username in ("admin", "school", "student", "user2", "user3")):
        messages.error(request, "僅測試帳號或管理員具備身分切換體驗權限")
        return redirect("courses:home")

    if role in User.Role.values:
        request.user.role = role
        if role == User.Role.ADMIN:
            request.user.is_staff = True
            request.user.is_superuser = True
        elif role == User.Role.SCHOOL:
            request.user.is_staff = True
            request.user.is_superuser = False
        else:
            request.user.is_staff = False
            request.user.is_superuser = False
        request.user.save(update_fields=["role", "is_staff", "is_superuser"])
        messages.success(request, f"已成功切換當前帳號身分為：【{request.user.get_role_display()}】！")
    return redirect("courses:home")
