from django.urls import path

from . import calendar_views, import_views, views

app_name = "selection"

urlpatterns = [
    path("calendar/", calendar_views.calendar_page, name="calendar"),
    path("calendar/events/new/", calendar_views.event_edit, name="event_new"),
    path("calendar/events/<int:pk>/", calendar_views.event_edit, name="event_edit"),
    path("calendar/events/<int:pk>/delete/", calendar_views.event_delete, name="event_delete"),
    path("import/excel/", import_views.excel_import, name="excel_import"),
    path("import/excel/confirm/", import_views.excel_confirm, name="excel_confirm"),
    path("import/excel/template/", import_views.excel_template, name="excel_template"),
    path("import/<int:pk>/undo/", import_views.undo_import, name="undo_import"),
    path("courses/clear/", import_views.clear_courses, name="clear_courses"),
    path("courses/clear-imported/", import_views.clear_imported, name="clear_imported"),

    path("timetable/", views.timetable, name="timetable"),
    path("timetable/student/<int:user_id>/", views.user_timetable, name="user_timetable"),
    path("timetable/print/", views.timetable_print, name="timetable_print"),
    path("course/<int:pk>/add/", views.course_add, name="course_add"),
    path("course/<int:pk>/remove/", views.course_remove, name="course_remove"),
    path("course/<int:pk>/pref/", views.course_update_pref, name="course_update_pref"),

    path("custom/add/", views.custom_schedule_add, name="custom_schedule_add"),
    path("custom/<int:pk>/update/", views.custom_schedule_update, name="custom_schedule_update"),
    path("custom/<int:pk>/delete/", views.custom_schedule_delete, name="custom_schedule_delete"),

    path("import/class/", views.import_class, name="import_class"),

    path("prelist/", views.prelist, name="prelist"),
    path("results/", views.results, name="results"),
    path("offering/<int:pk>/pre/", views.pre_add, name="pre_add"),
    path("prelist/<int:pk>/remove/", views.pre_remove, name="pre_remove"),

    path("console/", views.console_dashboard, name="console_dashboard"),
    path("console/offerings/", views.console_offerings, name="console_offerings"),
    path("console/offerings/<int:pk>/capacity/", views.console_capacity, name="console_capacity"),
    path("console/allocation/run/", views.console_run_allocation, name="console_run_allocation"),
    path("console/allocation/reset/", views.console_reset_allocation, name="console_reset_allocation"),
]
