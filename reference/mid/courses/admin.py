from django.contrib import admin

from .models import Course, Department, EduType, Offering, OfferingSlot, StudentClass


class OfferingSlotInline(admin.TabularInline):
    model = OfferingSlot
    extra = 0
    fields = ("weekday", "period", "start", "end", "room")


@admin.register(EduType)
class EduTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "edu")
    list_filter = ("edu",)
    search_fields = ("name", "code")


@admin.register(StudentClass)
class StudentClassAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "dept")
    list_filter = ("dept__edu",)
    search_fields = ("name", "code")
    autocomplete_fields = ("dept",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


@admin.register(Offering)
class OfferingAdmin(admin.ModelAdmin):
    list_display = ("course", "serial", "teacher", "capacity", "pre_count", "selected_count", "slots_summary")
    list_filter = ("classes__dept__edu",)
    search_fields = ("course__code", "course__name", "teacher")
    inlines = [OfferingSlotInline]
    filter_horizontal = ("classes",)
