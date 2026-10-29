from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import admin_role_required, school_role_required, student_role_required
from courses.models import Department, EduType, Offering, StudentClass

from .forms import CustomScheduleForm, ImportClassScheduleForm, SelectionPreferenceForm
from .models import CustomSchedule, Selection
from .services import (
    add_course_to_timetable,
    build_personal_timetable,
    check_custom_conflict,
    get_timetable_stats,
    import_class_timetable,
    redirect_back,
    remove_course_from_timetable,
    reset_allocation,
    run_allocation,
)


def _mobile_timetable_data(timetable_data, today_weekday=None):
    pass
    weekdays = ("週一", "週二", "週三", "週四", "週五", "週六", "週日")
    days = []
    for weekday, label in enumerate(weekdays, start=1):
        events = []
        for period_index, period in enumerate(timetable_data["periods"]):
            for item in timetable_data["grid"][period_index][weekday - 1]:
                events.append({
                    "id": f"{'custom' if item['is_custom'] else 'course'}-{item['id']}-{weekday}-{item['start']:%H%M}",
                    "name": item["name"],
                    "code": item["code"],
                    "period": item["period"],
                    "start": item["start"].strftime("%H:%M"),
                    "end": item["end"].strftime("%H:%M"),
                    "room": item["room"] or "",
                    "teacher": item["teacher"] or "",
                    "notes": item["notes"] or "",
                    "color": item["color"],
                    "isCustom": item["is_custom"],
                    "customId": item["id"] if item["is_custom"] else None,
                    "url": None if item["is_custom"] else reverse(
                        "courses:offering_detail", args=[item["offering_id"]]
                    ),
                })
        events.sort(key=lambda event: (event["start"], event["name"]))
        days.append({
            "weekday": weekday,
            "label": label,
            "isToday": weekday == today_weekday,
            "events": events,
        })
    return days


@login_required
@student_role_required
def timetable(request):
    return _render_timetable(request)


def _render_timetable(request, custom_form=None, editing_schedule=None, status=200):
    timetable_data = build_personal_timetable(request.user, full_grid=True)
    stats = get_timetable_stats(request.user)

    enrolled_courses = (
        request.user.selections.filter(status=Selection.Status.SELECTED)
        .select_related("offering", "offering__course")
        .prefetch_related("offering__slots")
        .order_by("offering__course__name")
    )
    custom_schedules = request.user.custom_schedules.all().order_by("weekday", "start")

    if custom_form is None:
        custom_form = CustomScheduleForm(initial={"weekday": timezone.localdate().isoweekday(), "start": "09:00", "end": "10:00"})
    import_form = ImportClassScheduleForm(
        initial={"student_class": request.user.student_class} if request.user.student_class else None
    )

    all_edus = EduType.objects.all().order_by("code")
    all_depts = Department.objects.select_related("edu").order_by("code")
    all_classes = StudentClass.objects.select_related("dept", "dept__edu").order_by("dept__edu__code", "dept__code", "code")

    User = request.user.__class__
    classmates = []
    if request.user.student_class:
        classmates = list(
            User.objects.filter(student_class=request.user.student_class, role=User.Role.STUDENT)
            .exclude(id=request.user.id)
            .order_by("username")
        )
    other_friends = list(
        User.objects.filter(role=User.Role.STUDENT)
        .exclude(id=request.user.id)
        .exclude(id__in=[c.id for c in classmates])
        .select_related("student_class", "student_class__dept")[:15]
    )

    context = {
        "active_tab": "timetable",
        "timetable": timetable_data,
        "stats": stats,
        "enrolled_courses": enrolled_courses,
        "custom_schedules": custom_schedules,
        "custom_form": custom_form,
        "can_edit_schedule": True,
        "editor_open": custom_form.is_bound,
        "editing_schedule": editing_schedule,
        "custom_action": reverse("selection:custom_schedule_update", args=[editing_schedule.pk]) if editing_schedule else reverse("selection:custom_schedule_add"),
        "schedule_editor_data": [
            {"id": item.pk, "title": item.title, "weekday": item.weekday,
             "period": item.period, "start": item.start.strftime("%H:%M"),
             "end": item.end.strftime("%H:%M"), "location": item.location,
             "color": item.color, "note": item.note,
             "updateUrl": reverse("selection:custom_schedule_update", args=[item.pk]),
             "deleteUrl": reverse("selection:custom_schedule_delete", args=[item.pk])}
            for item in custom_schedules
        ],
        "import_form": import_form,
        "all_edus": all_edus,
        "all_depts": all_depts,
        "all_classes": all_classes,
        "classmates": classmates,
        "other_friends": other_friends,
        "mobile_timetable_days": _mobile_timetable_data(
            timetable_data, today_weekday=stats["today_weekday"]
        ),
    }
    return render(request, "selection/timetable.html", context, status=status)


@login_required
def user_timetable(request, user_id):
    pass
    User = request.user.__class__
    target_user = get_object_or_404(User, pk=user_id, role=User.Role.STUDENT)
    timetable_data = build_personal_timetable(target_user, full_grid=True)
    stats = get_timetable_stats(target_user)
    enrolled_courses = (
        target_user.selections.filter(status=Selection.Status.SELECTED)
        .select_related("offering", "offering__course")
        .prefetch_related("offering__slots")
        .order_by("offering__course__name")
    )
    context = {
        "active_tab": "timetable",
        "target_user": target_user,
        "is_own_timetable": target_user == request.user,
        "timetable": timetable_data,
        "stats": stats,
        "enrolled_courses": enrolled_courses,
        "mobile_timetable_days": _mobile_timetable_data(
            timetable_data, today_weekday=stats["today_weekday"]
        ),
    }
    return render(request, "selection/user_timetable.html", context)


@login_required
@student_role_required
def course_add(request, pk):
    pass
    offering = get_object_or_404(Offering, pk=pk)
    code, msg = add_course_to_timetable(request.user, offering)
    if code == "ok":
        messages.success(request, msg)
    elif code == "duplicate":
        messages.info(request, msg)
    else:
        messages.error(request, msg)
    return redirect_back(request, fallback="courses:offering_detail", fallback_args=[offering.pk])


@login_required
@student_role_required
def course_remove(request, pk):
    pass
    removed = remove_course_from_timetable(request.user, pk)
    if removed:
        messages.success(request, "已從個人課表移除該課程")
    else:
        messages.warning(request, "未在你的課表中找到該課程")
    return redirect_back(request, fallback="selection:timetable")


@login_required
@student_role_required
def course_update_pref(request, pk):
    pass
    sel = get_object_or_404(Selection, user=request.user, offering_id=pk)
    if request.method == "POST":
        form = SelectionPreferenceForm(request.POST, instance=sel)
        if form.is_valid():
            form.save()
            messages.success(request, f"已更新「{sel.offering.course.name}」的自訂設定")
    return redirect_back(request, fallback="selection:timetable")


@login_required
@student_role_required
@require_POST
def custom_schedule_add(request):
    return _save_custom_schedule(request)


@login_required
@student_role_required
@require_POST
def custom_schedule_update(request, pk):
    item = get_object_or_404(CustomSchedule, pk=pk, user=request.user)
    return _save_custom_schedule(request, item)


def _save_custom_schedule(request, instance=None):
    form = CustomScheduleForm(request.POST, instance=instance)
    if not form.is_valid():
        return _render_timetable(request, custom_form=form, editing_schedule=instance, status=400)
    conflicts = check_custom_conflict(
        request.user, form.cleaned_data["weekday"], form.cleaned_data["start"],
        form.cleaned_data["end"], exclude_id=instance.pk if instance else None,
    )
    if conflicts:
        messages.warning(request, f"提醒：行程與現有排程重疊（{'；'.join(conflicts[:2])}）")
    item = form.save(commit=False)
    item.user = request.user
    item.save()
    messages.success(request, f"已{'更新' if instance else '新增'}個人行程「{item.title}」")
    return redirect("selection:timetable")


@login_required
@student_role_required
@require_POST
def custom_schedule_delete(request, pk):
    pass
    item = get_object_or_404(CustomSchedule, pk=pk, user=request.user)
    title = item.title
    item.delete()
    messages.success(request, f"已刪除個人行程「{title}」")
    return redirect_back(request, fallback="selection:timetable")


@login_required
@student_role_required
def import_class(request):
    pass
    if request.method == "POST":
        class_id = request.POST.get("student_class")
        if not class_id:
            messages.error(request, "請選擇欲匯入的班級！")
            return redirect("selection:timetable")

        target_class = get_object_or_404(StudentClass, pk=class_id)
        result = import_class_timetable(request.user, target_class)

        msg_parts = [f"班級「{target_class.name}」匯入完成：成功加入 {result['added']} 門課程"]
        if result["skipped"] > 0:
            msg_parts.append(f"略過 {result['skipped']} 門已在課表中的課程")
        if result["conflicts"]:
            msg_parts.append(f"因衝堂未加入 {len(result['conflicts'])} 門（{result['conflicts'][0]}）")

        messages.info(request, "，".join(msg_parts))
    return redirect("selection:timetable")


@login_required
@student_role_required
def timetable_print(request):
    pass
    timetable_data = build_personal_timetable(request.user, full_grid=True)
    stats = get_timetable_stats(request.user)
    enrolled_courses = (
        request.user.selections.filter(status=Selection.Status.SELECTED)
        .select_related("offering", "offering__course")
        .prefetch_related("offering__slots")
        .order_by("offering__course__name")
    )
    context = {
        "timetable": timetable_data,
        "stats": stats,
        "enrolled_courses": enrolled_courses,
        "user": request.user,
    }
    return render(request, "selection/timetable_print.html", context)



@login_required
@student_role_required
def prelist(request):
    return redirect("selection:timetable")


@login_required
@student_role_required
def results(request):
    return redirect("selection:timetable")


@login_required
@student_role_required
def pre_add(request, pk):
    return course_add(request, pk)


@login_required
@student_role_required
def pre_remove(request, pk):
    return course_remove(request, pk)



@login_required
@admin_role_required
def console_dashboard(request):
    total_pre = Selection.objects.filter(status=Selection.Status.PRE).count()
    total_selected = Selection.objects.filter(status=Selection.Status.SELECTED).count()
    context = {
        "active_tab": "console",
        "total_offering": Offering.objects.count(),
        "total_student": request.user.__class__.objects.filter(role="student").count(),
        "total_selected": total_selected,
        "total_pre": total_pre,
        "no_allocation": total_selected == 0 and total_pre > 0,
        "total_customs": CustomSchedule.objects.count(),
        "hot_offerings": (
            Offering.objects.annotate(
                selected_n=models.Count("selections", filter=models.Q(selections__status=Selection.Status.SELECTED)),
                pre_n=models.Count("selections", filter=models.Q(selections__status=Selection.Status.PRE)),
            )
            .select_related("course")
            .order_by("-pre_n")[:10]
        ),
    }
    return render(request, "selection/console_dashboard.html", context)


@login_required
@school_role_required
def console_offerings(request):
    q = request.GET.get("q", "").strip()
    qs = Offering.objects.select_related("course").prefetch_related("slots").order_by("course__code", "serial")
    if q:
        qs = qs.filter(models.Q(course__name__icontains=q) | models.Q(course__code__icontains=q) | models.Q(teacher__icontains=q))

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    get_copy = request.GET.copy()
    get_copy.pop("page", None)
    context = {"active_tab": "console", "page_obj": page_obj, "q": q, "query_string": get_copy.urlencode()}
    return render(request, "selection/console_offerings.html", context)


@login_required
@school_role_required
def console_capacity(request, pk):
    offering = get_object_or_404(Offering, pk=pk)
    if request.method == "POST":
        try:
            new_capacity = int(request.POST.get("capacity", ""))
            if not 0 <= new_capacity <= 9999:
                raise ValueError
            offering.capacity = new_capacity
            offering.save(update_fields=["capacity"])
            messages.success(request, f"已更新「{offering.display_name}」名額為 {new_capacity}")
        except (TypeError, ValueError):
            messages.error(request, "名額必須是 0–9999 的整數")
    return redirect(request.META.get("HTTP_REFERER") or "selection:console_offerings")


@login_required
@admin_role_required
def console_run_allocation(request):
    if request.method == "POST":
        stats = run_allocation()
        messages.success(
            request,
            f"分發完成：共處理 {stats['offerings']} 門開課，正取 {stats['selected']} 筆，未選上 {stats['rejected']} 筆",
        )
    return redirect("selection:console_dashboard")


@login_required
@admin_role_required
def console_reset_allocation(request):
    if request.method == "POST":
        n = reset_allocation()
        messages.info(request, f"已重置 {n} 筆選課紀錄回「預選中」")
    return redirect("selection:console_dashboard")
