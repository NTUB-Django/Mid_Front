from django.urls import path

from . import group_views, social_views, views

app_name = "accounts"

urlpatterns = [
    path("groups/<int:pk>/", group_views.workspace, name="group_workspace"),
    path("groups/<int:pk>/events/create/", group_views.event_create, name="group_event_create"),
    path("groups/<int:pk>/events/<int:item_id>/edit/", group_views.event_edit, name="group_event_edit"),
    path("groups/<int:pk>/events/<int:item_id>/delete/", group_views.event_delete, name="group_event_delete"),
    path("groups/<int:pk>/tasks/create/", group_views.task_create, name="group_task_create"),
    path("groups/<int:pk>/tasks/<int:item_id>/toggle/", group_views.task_toggle, name="group_task_toggle"),
    path("groups/<int:pk>/tasks/<int:item_id>/delete/", group_views.task_delete, name="group_task_delete"),
    path("groups/<int:pk>/memos/create/", group_views.memo_create, name="group_memo_create"),
    path("groups/<int:pk>/memos/<int:item_id>/edit/", group_views.memo_edit, name="group_memo_edit"),
    path("groups/<int:pk>/memos/<int:item_id>/delete/", group_views.memo_delete, name="group_memo_delete"),
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
    path("logout/", views.StudentLogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    path("profile/", views.profile, name="profile"),
    path("roles/", views.manage_roles, name="manage_roles"),
]
