from django.conf import settings
from django.contrib.auth import logout
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.cache import patch_cache_control


def session_scope(path):
    if path == "/admin" or path.startswith("/admin/"):
        return "admin", "/admin/"
    if path == "/school" or path.startswith("/school/"):
        return "school", "/school/"
    return "student", "/"


class ScopedSessionMiddleware(SessionMiddleware):
    def process_request(self, request):
        scope, cookie_path = session_scope(request.path_info)
        request.session_scope = scope
        request.session_cookie_path = cookie_path
        request.session_cookie_name = "mid_" + scope + "_session"
        cookie_name = settings.SESSION_COOKIE_NAME
        scoped_value = request.COOKIES.get(request.session_cookie_name)
        if scoped_value:
            request.COOKIES[cookie_name] = scoped_value
        else:
            request.COOKIES.pop(cookie_name, None)
        super().process_request(request)

    def process_response(self, request, response):
        response = super().process_response(request, response)
        cookie = response.cookies.pop(settings.SESSION_COOKIE_NAME, None)
        if cookie is not None:
            response.cookies[request.session_cookie_name] = cookie.value
            scoped = response.cookies[request.session_cookie_name]
            for attribute in cookie.keys():
                scoped[attribute] = cookie[attribute]
            scoped["path"] = request.session_cookie_path
        return response


class RoleSessionBoundaryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated:
            scope = request.session_scope
            allowed = (
                (scope == "admin" and user.is_superuser and user.is_admin_role)
                or (scope == "school" and user.is_school_role)
                or (scope == "student" and user.is_student_role)
            )
            if not allowed:
                logout(request)
                if scope == "admin":
                    return HttpResponseRedirect(reverse("admin:login"))
                if scope == "school":
                    return HttpResponseRedirect(reverse("school:login"))
                return HttpResponseRedirect(reverse("accounts:login"))
        response = self.get_response(request)
        if response.get("Content-Type", "").startswith("text/html") or 300 <= response.status_code < 400:
            patch_cache_control(response, private=True, no_store=True, no_cache=True, must_revalidate=True)
        return response
