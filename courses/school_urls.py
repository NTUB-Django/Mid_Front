from django.urls import path

from . import school_import, school_views

app_name = "school"

urlpatterns = [
    path("", school_views.dashboard, name="dashboard"),
    path("login/", school_views.SchoolLoginView.as_view(), name="login"),
    path("logout/", school_views.SchoolLogoutView.as_view(), name="logout"),
    path("profile/", school_views.profile, name="profile"),
    path("students/import/", school_import.student_import, name="student_import"),
    path("students/import/confirm/", school_import.student_import_confirm, name="student_import_confirm"),
    path("students/import/template/", school_import.student_import_template, name="student_import_template"),
    path("classes/", school_views.class_timetables, name="classes"),
    path("offerings/", school_views.offerings, name="offerings"),
    path("offerings/<int:pk>/capacity/", school_views.capacity, name="capacity"),
    path("offerings/<int:pk>/", school_views.offering_detail, name="offering_detail"),
    path("offerings/<int:pk>/roster/", school_views.offering_roster, name="offering_roster"),
    path("courses/", school_views.browse, name="browse"),
]
