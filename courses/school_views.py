from functools import wraps

from django.contrib.auth import views as auth_views
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache

from accounts.forms import CaptchaAuthenticationForm
from accounts import views as account_views
from courses import views as course_views
from selection import views as selection_views


def school_required(view):
    @wraps(view)
    def guarded(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_school_role:
            return redirect("school:login")
        return view(request, *args, **kwargs)
    return never_cache(guarded)


class SchoolLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = CaptchaAuthenticationForm
    next_page = "school:dashboard"

    def form_valid(self, form):
        if not form.get_user().is_school_role:
            form.add_error(None, "請使用教務人員 Email 登入。")
            return self.form_invalid(form)
        response = super().form_valid(form)
        self.request.session.set_expiry(60 * 60 * 24 * 14 if self.request.POST.get("remember_me") else 0)
        messages.success(self.request, "學校端登入成功。")
        return response


@school_required
def dashboard(request):
    return course_views.home(request)


@school_required
def class_timetables(request):
    return course_views.class_timetables(request)


@school_required
def offerings(request):
    return selection_views.console_offerings(request)


@school_required
def capacity(request, pk):
    return selection_views.console_capacity(request, pk)


@school_required
def browse(request):
    return course_views.browse(request)


@school_required
def offering_detail(request, pk):
    return course_views.offering_detail(request, pk)


@school_required
def offering_roster(request, pk):
    return course_views.offering_roster(request, pk)


@school_required
def profile(request):
    return account_views.profile(request)


class SchoolLogoutView(auth_views.LogoutView):
    next_page = "school:login"

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.success(request, "已安全登出學校端。")
        return response
