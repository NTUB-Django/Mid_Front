from django.urls import path

from . import views

app_name = "courses"

urlpatterns = [
    path("", views.home, name="home"),
    path("courses/browse/", views.browse, name="browse"),
    path("courses/offering/<int:pk>/", views.offering_detail, name="offering_detail"),
    path("courses/offering/<int:pk>/roster/", views.offering_roster, name="offering_roster"),
    path("timetables/classes/", views.class_timetables, name="class_timetables"),
]
