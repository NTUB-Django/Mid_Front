from django.contrib.auth.backends import ModelBackend
from .models import User


class UsernameOrEmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = (username or kwargs.get(User.USERNAME_FIELD) or "").strip()
        if not identifier or password is None:
            return None
        if identifier == "admin":
            candidates = list(User.objects.filter(username="admin", role=User.Role.ADMIN, is_superuser=True)[:2])
        else:
            candidates = list(User.objects.filter(email__iexact=identifier).exclude(email="")[:2])
        if len(candidates) != 1:
            User().set_password(password)
            return None
        user = candidates[0]
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
