from datetime import time
from io import BytesIO
import secrets
import time as timestamp

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from accounts.decorators import student_role_required

from .excel import parse_upload
from .models import CustomSchedule, ImportBatch, Selection
from .services import check_custom_conflict, get_user_enrolled_slots, time_intervals_overlap


def duplicate(user, row):
    values = {key: row[key] for key in ["title", "weekday", "start", "end", "location"]}
    if user.custom_schedules.filter(**values).exists():
        return True
    return get_user_enrolled_slots(user).filter(offering__course__name=row["title"], weekday=row["weekday"], start=row["start"], end=row["end"]).exists()


@never_cache
@login_required
@student_role_required
def excel_import(request):
    context = {"active_tab": "timetable"}
    if request.method == "POST":
        request.session.pop("excel_import_preview", None)
        upload = request.FILES.get("file")
        try:
            if upload is None:
                raise ValidationError("請選擇學校匯出的 Excel 檔案。")
            rows, errors = parse_upload(upload)
        except ValidationError as error:
            context["errors"] = error.messages
            return render(request, "selection/excel_import.html", context, status=400)
        preview = []
        for index, row in enumerate(rows):
            conflicts = check_custom_conflict(request.user, row["weekday"], time.fromisoformat(row["start"]), time.fromisoformat(row["end"]))
            for previous in rows[:index]:
                if previous["weekday"] == row["weekday"] and time_intervals_overlap(time.fromisoformat(previous["start"]), time.fromisoformat(previous["end"]), time.fromisoformat(row["start"]), time.fromisoformat(row["end"])):
                    conflicts.append(f"與同檔案「{previous['title']}」時間重疊")
            preview.append({**row, "duplicate": duplicate(request.user, row), "conflicts": conflicts})
        token = secrets.token_urlsafe(24)
        request.session["excel_import_preview"] = {"rows": rows, "token": token, "created": timestamp.time(), "name": upload.name[:120]}
        context.update({"preview": preview, "token": token, "file_name": upload.name, "parse_errors": errors})
    return render(request, "selection/excel_import.html", context)


@login_required
@student_role_required
@require_POST
@transaction.atomic
def excel_confirm(request):
    preview = request.session.get("excel_import_preview")
    if not preview or not secrets.compare_digest(str(request.POST.get("token", "")), preview["token"]) or timestamp.time() - preview["created"] > 900:
        messages.error(request, "匯入預覽已失效，請重新上傳檔案。")
        return redirect("selection:excel_import")
    request.session.pop("excel_import_preview", None)
    batch = ImportBatch.objects.create(user=request.user, source="excel", label=preview["name"])
    added = duplicates = conflicts = 0
    for row in preview["rows"]:
        if duplicate(request.user, row):
            duplicates += 1
            continue
        overlap = check_custom_conflict(request.user, row["weekday"], time.fromisoformat(row["start"]), time.fromisoformat(row["end"]))
        if overlap and request.POST.get("skip_conflicts") == "yes":
            conflicts += 1
            continue
        _, created = CustomSchedule.objects.get_or_create(user=request.user, import_source="excel", **{key: row[key] for key in ["title", "weekday", "start", "end", "location"]}, defaults={"note": row["note"], "color": "blue", "import_batch": batch})
        added += int(created)
        duplicates += int(not created)
    if not added:
        batch.delete()
    message = f"Excel 匯入完成：新增 {added} 個上課時段，略過重複 {duplicates} 個、衝堂 {conflicts} 個。可在匯入紀錄撤銷本次匯入。"
    notifier = messages.info if conflicts else messages.success
    notifier(request, message, extra_tags="schedule-conflict schedule-import" if conflicts else "")
    return redirect("selection:timetable")


@login_required
@student_role_required
def excel_template(request):
    from openpyxl import Workbook
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "匯入課表"
    sheet.append(["課程名稱", "星期", "開始時間", "結束時間", "教室", "教師", "備註"])
    sheet.append(["程式設計", "週一", "08:10", "10:00", "資管301", "王老師", "範例資料，匯入前請替換"])
    sheet.freeze_panes = "A2"
    for column in "ABCDEFG":
        sheet.column_dimensions[column].width = 23
    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()
    response = HttpResponse(buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="timetable-import-template.xlsx"'
    return response


@login_required
@student_role_required
@require_POST
@transaction.atomic
def undo_import(request, pk):
    batch = get_object_or_404(ImportBatch, pk=pk, user=request.user)
    courses = request.user.selections.filter(import_batch=batch)
    schedules = request.user.custom_schedules.filter(import_batch=batch)
    count = courses.count() + schedules.count()
    courses.delete()
    schedules.delete()
    batch.delete()
    messages.success(request, f"已撤銷本次匯入，共移除 {count} 筆；其他課程與個人行程保留。")
    return redirect("selection:timetable")


@login_required
@student_role_required
@require_POST
@transaction.atomic
def clear_courses(request):
    courses = request.user.selections.filter(status=Selection.Status.SELECTED)
    imported = request.user.custom_schedules.filter(import_source="excel")
    count = courses.count() + imported.count()
    courses.delete()
    imported.delete()
    request.user.import_batches.filter(selections__isnull=True, schedules__isnull=True).delete()
    messages.success(request, f"已清空 {count} 筆已加入課程／Excel 上課時段；個人行程與預選資料保留。")
    return redirect("selection:timetable")


@login_required
@student_role_required
@require_POST
@transaction.atomic
def clear_imported(request):
    courses = request.user.selections.filter(import_batch__isnull=False)
    schedules = request.user.custom_schedules.filter(import_source="excel")
    count = courses.count() + schedules.count()
    courses.delete()
    schedules.delete()
    request.user.import_batches.filter(selections__isnull=True, schedules__isnull=True).delete()
    messages.success(request, f"已批次刪除 {count} 筆匯入課程；手動加入的課程與個人行程保留。")
    return redirect("selection:timetable")
