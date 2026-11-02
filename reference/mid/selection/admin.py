from django.contrib import admin

from .models import AcademicTerm, CustomSchedule, PersonalEvent, Selection
from .services import reset_allocation, run_allocation


@admin.action(description="對預選中的課程執行分發抽籤")
def run_allocation_action(modeladmin, request, queryset):
    stats = run_allocation()
    modeladmin.message_user(
        request,
        f"分發完成：正取 {stats['selected']} 筆，未選上 {stats['rejected']} 筆（{stats['offerings']} 門開課）",
    )


@admin.action(description="重置全部選課為「預選中」")
def reset_allocation_action(modeladmin, request, queryset):
    n = reset_allocation()
    modeladmin.message_user(request, f"已重置 {n} 筆選課紀錄回「預選中」")


@admin.register(Selection)
class SelectionAdmin(admin.ModelAdmin):
    list_display = ("user", "offering", "status", "color", "notes", "created_at")
    list_filter = ("status", "color")
    search_fields = ("user__username", "user__display_name", "offering__course__name", "offering__course__code")
    readonly_fields = ("created_at",)
    actions = [run_allocation_action, reset_allocation_action]


@admin.register(CustomSchedule)
class CustomScheduleAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "weekday", "period", "start", "end", "location", "color", "created_at")
    list_filter = ("weekday", "color")
    search_fields = ("user__username", "user__display_name", "title", "location", "note")
    readonly_fields = ("created_at", "updated_at")


@admin.register(PersonalEvent)
class PersonalEventAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "starts_at", "ends_at", "visibility", "color")
    list_filter = ("visibility", "color")
    search_fields = ("user__username", "user__email", "title")
    readonly_fields = ("created_at", "updated_at")


@admin.register(AcademicTerm)
class AcademicTermAdmin(admin.ModelAdmin):
    list_display = ("name", "starts_on", "ends_on", "is_current")
    list_filter = ("is_current",)
