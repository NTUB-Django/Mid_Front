from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import user_passes_test


def admin_role_required(view_func=None, redirect_field_name=REDIRECT_FIELD_NAME):
    pass
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.is_admin_role,
        login_url="accounts:login",
        redirect_field_name=redirect_field_name,
    )
    if view_func:
        return actual_decorator(view_func)
    return actual_decorator


def school_role_required(view_func=None, redirect_field_name=REDIRECT_FIELD_NAME):
    pass
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and (u.is_school_role or u.is_admin_role),
        login_url="accounts:login",
        redirect_field_name=redirect_field_name,
    )
    if view_func:
        return actual_decorator(view_func)
    return actual_decorator


def student_role_required(view_func=None, redirect_field_name=REDIRECT_FIELD_NAME):
    pass
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.is_student_role,
        login_url="accounts:login",
        redirect_field_name=redirect_field_name,
    )
    if view_func:
        return actual_decorator(view_func)
    return actual_decorator
