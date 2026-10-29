from django.contrib.auth import views as auth_views
from django.urls import path

from . import social_views, views

app_name = "accounts"

urlpatterns = [
    path("connections/", social_views.connections, name="connections"),
    path("privacy/", social_views.privacy, name="privacy"),
    path("friends/request/", social_views.friend_request, name="friend_request"),
    path("friends/<int:pk>/<str:action>/", social_views.friend_action, name="friend_action"),
    path("groups/create/", social_views.group_create, name="group_create"),
    path("groups/<int:pk>/invite/", social_views.group_invite, name="group_invite"),
    path("groups/<int:pk>/delete/", social_views.group_delete, name="group_delete"),
    path("memberships/<int:pk>/<str:action>/", social_views.membership_action, name="membership_action"),
    path(
        "login/",
        views.StudentLoginView.as_view(),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    path("profile/", views.profile, name="profile"),
    path("roles/", views.manage_roles, name="manage_roles"),
    path("switch-role/<str:role>/", views.switch_role, name="switch_role"),
]
