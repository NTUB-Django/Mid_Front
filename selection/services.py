from datetime import datetime, time
import random

from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from courses.models import Offering, OfferingSlot

from .models import CustomSchedule, Selection


STANDARD_PERIODS = [
    ("第一節", time(8, 10), time(9, 0)),
    ("第二節", time(9, 10), time(10, 0)),
    ("第三節", time(10, 10), time(11, 0)),
    ("第四節", time(11, 10), time(12, 0)),
    ("第五節", time(13, 30), time(14, 20)),
    ("第六節", time(14, 25), time(15, 15)),
    ("第七節", time(15, 25), time(16, 15)),
    ("第八節", time(16, 20), time(17, 10)),
    ("第九節", time(17, 15), time(18, 5)),
    ("第十節", time(18, 30), time(19, 15)),
    ("第十一節", time(19, 20), time(20, 5)),
    ("第十二節", time(20, 15), time(21, 0)),
    ("第十三節", time(21, 5), time(21, 50)),
]


def time_intervals_overlap(start1, end1, start2, end2):
    return start1 < end2 and start2 < end1


def get_user_selection_map(user, offering_ids):
    if not offering_ids or not user.is_authenticated:
        return {}
    return dict(
        Selection.objects.filter(user=user, offering_id__in=offering_ids).values_list("offering_id", "status")
    )


def get_user_enrolled_slots(user):
    return (
        OfferingSlot.objects.filter(
            offering__selections__user=user,
            offering__selections__status=Selection.Status.SELECTED,
        )
        .select_related("offering", "offering__course")
        .distinct()
    )


def check_conflicts(offering, user):
    conflicts = []
    enrolled_slots = get_user_enrolled_slots(user)


    for slot in offering.slots.all():
        for other in enrolled_slots:
            if other.offering_id == offering.id:
                continue
            if slot.weekday == other.weekday and time_intervals_overlap(slot.start, slot.end, other.start, other.end):
                conflicts.append(f"{slot.get_weekday_display()} {slot.start:%H:%M}–{slot.end:%H:%M} 與「{other.offering.course.name}」（{other.start:%H:%M}–{other.end:%H:%M}）衝堂")


    customs = user.custom_schedules.all()
    for slot in offering.slots.all():
        for c in customs:
            if slot.weekday == c.weekday and time_intervals_overlap(slot.start, slot.end, c.start, c.end):
                conflicts.append(f"{slot.get_weekday_display()} {slot.start:%H:%M}–{slot.end:%H:%M} 與個人行程「{c.title}」（{c.start:%H:%M}–{c.end:%H:%M}）衝堂")

    return conflicts


def check_custom_conflict(user, weekday, start, end, exclude_id=None):
    conflicts = []


    for other in get_user_enrolled_slots(user):
        if other.weekday == weekday and time_intervals_overlap(start, end, other.start, other.end):
            conflicts.append(f"{other.get_weekday_display()} 與既有課程「{other.offering.course.name}」（{other.start:%H:%M}–{other.end:%H:%M}）衝堂")


    customs = user.custom_schedules.exclude(id=exclude_id) if exclude_id else user.custom_schedules.all()
    for c in customs:
        if c.weekday == weekday and time_intervals_overlap(start, end, c.start, c.end):
            conflicts.append(f"{c.get_weekday_display()} 與個人行程「{c.title}」（{c.start:%H:%M}–{c.end:%H:%M}）衝堂")

    return conflicts


@transaction.atomic
def add_course_to_timetable(user, offering):
    sel = Selection.objects.filter(user=user, offering=offering).first()
    if sel and sel.status == Selection.Status.SELECTED:
        return "duplicate", f"「{offering.display_name}」已在你的個人課表中"

    conflicts = check_conflicts(offering, user)
    if conflicts:
        clash = "；".join(conflicts)
        return "conflict", f"加入失敗，發現衝堂：{clash}"

    if sel:
        sel.status = Selection.Status.SELECTED
        sel.save(update_fields=["status"])
        return "ok", f"已將「{offering.display_name}」更新加入個人課表！"

    Selection.objects.create(
        user=user,
        offering=offering,
        status=Selection.Status.SELECTED,
    )
    return "ok", f"已成功加入個人課表：{offering.display_name}"


def remove_course_from_timetable(user, offering_id):
    offering = get_object_or_404(Offering, pk=offering_id)
    deleted, _ = Selection.objects.filter(user=user, offering=offering).delete()
    return deleted > 0


@transaction.atomic
def import_class_timetable(user, student_class):
    offerings = student_class.offerings.select_related("course").prefetch_related("slots").all()
    added = 0
    skipped = 0
    conflicts = []

    for off in offerings:
        if Selection.objects.filter(user=user, offering=off).exists():
            skipped += 1
            continue
        c = check_conflicts(off, user)
        if c:
            conflicts.append(f"{off.display_name}（{c[0]}）")
            continue
        Selection.objects.create(user=user, offering=off, status=Selection.Status.SELECTED)
        added += 1

    return {"added": added, "skipped": skipped, "conflicts": conflicts}


def build_personal_timetable(user, full_grid=True):

    selections = (
        user.selections.filter(status=Selection.Status.SELECTED)
        .select_related("offering", "offering__course")
        .prefetch_related("offering__slots")
    )

    customs = user.custom_schedules.all()

    items = []

    for sel in selections:
        for slot in sel.offering.slots.all():
            items.append(
                {
                    "is_custom": False,
                    "id": sel.id,
                    "offering_id": sel.offering_id,
                    "name": slot.offering.course.name,
                    "code": slot.offering.course.code,
                    "serial": slot.offering.serial,
                    "teacher": slot.offering.teacher,
                    "room": slot.room,
                    "color": sel.color or "terracotta",
                    "notes": sel.notes,
                    "weekday": slot.weekday,
                    "period": slot.period,
                    "start": slot.start,
                    "end": slot.end,
                }
            )


    for c in customs:
        items.append(
            {
                "is_custom": True,
                "id": c.id,
                "offering_id": None,
                "name": c.title,
                "code": "自訂行程",
                "serial": "",
                "teacher": "",
                "room": c.location,
                "color": c.color or "blue",
                "notes": c.note,
                "weekday": c.weekday,
                "period": c.period or f"{c.start:%H:%M}–{c.end:%H:%M}",
                "start": c.start,
                "end": c.end,
            }
        )


    has_weekend = any(item["weekday"] in (6, 7) for item in items)
    has_evening = any(item["end"] > time(18, 5) for item in items)


    if full_grid:
        if has_evening:
            base_periods = list(STANDARD_PERIODS)
        else:
            base_periods = list(STANDARD_PERIODS[:9])
    else:

        distinct_p = sorted({(i["period"], i["start"], i["end"]) for i in items}, key=lambda x: x[1])
        base_periods = distinct_p or list(STANDARD_PERIODS[:8])


    period_keys = [p[0] for p in base_periods]
    for it in items:
        p_name = it["period"]
        if p_name not in period_keys:

            base_periods.append((p_name, it["start"], it["end"]))
            base_periods.sort(key=lambda x: x[1])
            period_keys = [p[0] for p in base_periods]

    period_index = {p[0]: i for i, p in enumerate(base_periods)}
    grid = {i: {d: [] for d in range(7)} for i in range(len(base_periods))}

    for it in items:
        row_idx = period_index.get(it["period"])
        if row_idx is not None and 1 <= it["weekday"] <= 7:
            grid[row_idx][it["weekday"] - 1].append(it)

    return {
        "periods": base_periods,
        "grid": grid,
        "has_weekend": has_weekend,
        "total_items": len(items),
    }


def get_timetable_stats(user):
    selections = (
        user.selections.filter(status=Selection.Status.SELECTED)
        .select_related("offering", "offering__course")
        .prefetch_related("offering__slots")
    )
    customs = user.custom_schedules.all()

    total_course_count = selections.count()
    total_custom_count = customs.count()

    total_periods = 0
    weekday_counts = {i: 0 for i in range(1, 8)}

    today_weekday = timezone.localtime(timezone.now()).isoweekday()
    today_items = []

    for sel in selections:
        slots = sel.offering.slots.all()
        total_periods += len(slots)
        for s in slots:
            weekday_counts[s.weekday] += 1
            if s.weekday == today_weekday:
                today_items.append(
                    {
                        "is_custom": False,
                        "title": sel.offering.course.name,
                        "time_str": f"{s.period}（{s.start:%H:%M}–{s.end:%H:%M}）",
                        "start": s.start,
                        "room": s.room,
                        "teacher": sel.offering.teacher,
                        "color": sel.color,
                        "id": sel.offering_id,
                    }
                )

    for c in customs:
        total_periods += 1
        weekday_counts[c.weekday] += 1
        if c.weekday == today_weekday:
            today_items.append(
                {
                    "is_custom": True,
                    "title": c.title,
                    "time_str": f"{c.start:%H:%M}–{c.end:%H:%M}",
                    "start": c.start,
                    "room": c.location,
                    "teacher": "",
                    "color": c.color,
                    "id": c.id,
                }
            )

    today_items.sort(key=lambda x: x["start"])


    course_credits = sum(sel.offering.slots.count() for sel in selections)

    return {
        "total_courses": total_course_count,
        "total_customs": total_custom_count,
        "total_credits": course_credits,
        "total_weekly_periods": total_periods,
        "weekday_counts": weekday_counts,
        "today_weekday": today_weekday,
        "today_items": today_items,
    }


def build_class_timetable(student_class):
    pass
    offerings = student_class.offerings.select_related("course").prefetch_related("slots").all()
    items = []
    for off in offerings:
        for slot in off.slots.all():
            items.append({
                "is_custom": False,
                "id": off.id,
                "offering_id": off.id,
                "name": off.course.name,
                "code": off.course.code,
                "serial": off.serial,
                "teacher": off.teacher,
                "room": slot.room,
                "color": "terracotta",
                "notes": "",
                "weekday": slot.weekday,
                "period": slot.period,
                "start": slot.start,
                "end": slot.end,
            })
    base_periods = list(STANDARD_PERIODS[:9])
    period_keys = [p[0] for p in base_periods]
    for it in items:
        if it["period"] not in period_keys:
            base_periods.append((it["period"], it["start"], it["end"]))
            base_periods.sort(key=lambda x: x[1])
            period_keys = [p[0] for p in base_periods]

    period_index = {p[0]: i for i, p in enumerate(base_periods)}
    grid = {i: {d: [] for d in range(7)} for i in range(len(base_periods))}
    for it in items:
        row_idx = period_index.get(it["period"])
        if row_idx is not None and 1 <= it["weekday"] <= 7:
            grid[row_idx][it["weekday"] - 1].append(it)

    return {
        "periods": base_periods,
        "grid": grid,
        "has_weekend": any(item["weekday"] in (6, 7) for item in items),
        "total_items": len(items),
    }



def build_timetable(user, statuses):

    if Selection.Status.SELECTED in statuses:
        return build_personal_timetable(user, full_grid=True)

    selections = (
        user.selections.filter(status__in=statuses)
        .select_related("offering", "offering__course")
        .prefetch_related("offering__slots")
    )
    slots = []
    for sel in selections:
        for slot in sel.offering.slots.all():
            slots.append(
                {
                    "weekday": slot.weekday,
                    "period": slot.period,
                    "start": slot.start,
                    "end": slot.end,
                    "room": slot.room,
                    "offering": slot.offering,
                    "course_name": slot.offering.course.name,
                    "course_code": slot.offering.course.code,
                    "teacher": slot.offering.teacher,
                    "status": sel.status,
                }
            )

    periods = sorted({(s["period"], s["start"], s["end"]) for s in slots}, key=lambda p: p[1])
    if not periods:
        periods = list(STANDARD_PERIODS[:8])
    period_index = {p[0]: i for i, p in enumerate(periods)}

    grid = {i: {d: [] for d in range(7)} for i in range(len(periods))}
    for s in slots:
        if s["period"] in period_index:
            grid[period_index[s["period"]]][s["weekday"] - 1].append(s)

    return {"periods": periods, "grid": grid, "has_weekend": any(s["weekday"] in (6, 7) for s in slots)}


def add_to_prelist(user, offering):
    return add_course_to_timetable(user, offering)


def remove_from_prelist(user, offering_id):
    return remove_course_from_timetable(user, offering_id)


def run_allocation():
    stats = {"offerings": 0, "selected": 0, "rejected": 0}
    with transaction.atomic():
        offering_ids = (
            Selection.objects.filter(status=Selection.Status.PRE)
            .values_list("offering", flat=True)
            .distinct()
        )
        for offering_id in offering_ids:
            offering = Offering.objects.select_for_update().get(pk=offering_id)
            pre_list = list(
                Selection.objects.filter(offering=offering, status=Selection.Status.PRE).select_for_update()
            )
            if not pre_list:
                continue
            capacity = offering.capacity or 0
            random.shuffle(pre_list)
            winners, losers = pre_list[:capacity], pre_list[capacity:]
            for s in winners:
                s.status = Selection.Status.SELECTED
            for s in losers:
                s.status = Selection.Status.REJECTED
            Selection.objects.bulk_update(winners + losers, ["status"])
            stats["offerings"] += 1
            stats["selected"] += len(winners)
            stats["rejected"] += len(losers)
    return stats


def reset_allocation():
    n = Selection.objects.exclude(status=Selection.Status.PRE).update(status=Selection.Status.PRE)
    return n


def redirect_back(request: HttpRequest, fallback="selection:timetable", fallback_args=None):
    ref = request.META.get("HTTP_REFERER")
    if ref and ref.startswith(f"{request.scheme}://{request.get_host()}"):
        return redirect(ref)
    return redirect(fallback, *fallback_args if fallback_args else [])
