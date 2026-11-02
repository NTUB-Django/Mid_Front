import calendar
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import student_role_required
from accounts.models import GroupEvent
from .forms import PersonalEventForm
from .models import AcademicTerm, EVENT_COLORS, PersonalEvent, Selection


def current_term():
    return AcademicTerm.objects.filter(is_current=True).order_by("-starts_on").first()


def scheduled_class_day(day, term):
    return bool(term and term.starts_on <= day <= term.ends_on and day.isoformat() not in term.excluded_dates)


def calendar_entries(user, first, last):
    term = current_term()
    entries = defaultdict(list)
    selections = user.selections.filter(status=Selection.Status.SELECTED).select_related("offering__course").prefetch_related("offering__slots")
    weekly = user.custom_schedules.all()
    start_at = timezone.make_aware(datetime.combine(first, time.min))
    end_at = timezone.make_aware(datetime.combine(last + timedelta(days=1), time.min))
    personal = user.personal_events.filter(starts_at__lt=end_at, ends_at__gt=start_at)
    groups = GroupEvent.objects.filter(Q(group__owner=user) | Q(group__memberships__user=user, group__memberships__accepted=True), starts_at__lt=end_at, ends_at__gt=start_at).distinct().select_related("group")
    day = first
    while day <= last:
        if scheduled_class_day(day, term):
            for selection in selections:
                for slot in selection.offering.slots.all():
                    if slot.weekday == day.isoweekday():
                        entries[day].append({"kind": "課程", "title": selection.offering.course.name, "start": slot.start, "end": slot.end, "location": slot.room, "color": "#2563eb", "url": reverse("courses:offering_detail", args=[selection.offering_id])})
        for item in weekly:
            if item.weekday == day.isoweekday() and (item.import_source != "excel" or scheduled_class_day(day, term)):
                entries[day].append({"kind": "匯入課程" if item.import_source == "excel" else "每週行程", "title": item.title, "start": item.start, "end": item.end, "location": item.location, "color": item.palette["hex"], "url": reverse("selection:timetable")})
        for item in personal:
            begins = timezone.localtime(item.starts_at)
            ends = timezone.localtime(item.ends_at)
            if begins.date() <= day <= ends.date():
                entries[day].append({"kind": "個人行程", "title": item.title, "start": begins.time().replace(tzinfo=None) if begins.date() == day else time.min, "end": ends.time().replace(tzinfo=None) if ends.date() == day else time.max, "location": item.location, "color": item.palette["hex"], "url": reverse("selection:event_edit", args=[item.pk])})
        for item in groups:
            begins = timezone.localtime(item.starts_at)
            ends = timezone.localtime(item.ends_at)
            if begins.date() <= day <= ends.date():
                entries[day].append({"kind": item.group.name, "title": item.title, "start": begins.time().replace(tzinfo=None) if begins.date() == day else time.min, "end": ends.time().replace(tzinfo=None) if ends.date() == day else time.max, "location": item.location, "color": EVENT_COLORS.get(item.color, EVENT_COLORS["blue"])["hex"], "url": reverse("accounts:group_workspace", args=[item.group_id])})
        entries[day].sort(key=lambda item: (item["start"], item["title"]))
        day += timedelta(days=1)
    return entries


@login_required
@student_role_required
def calendar_page(request):
    mode = request.GET.get("view", "week")
    if mode not in {"day", "week", "month", "list"}:
        mode = "week"
    try:
        anchor = date.fromisoformat(request.GET.get("date", ""))
    except ValueError:
        anchor = timezone.localdate()
    if mode == "month":
        weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(anchor.year, anchor.month)
        days = [day for week in weeks for day in week]
        first, last = days[0], days[-1]
        previous = (anchor.replace(day=1) - timedelta(days=1)).replace(day=1)
        following = (anchor.replace(day=28) + timedelta(days=4)).replace(day=1)
    elif mode == "week":
        first = anchor - timedelta(days=anchor.weekday())
        last = first + timedelta(days=6)
        days = [first + timedelta(days=offset) for offset in range(7)]
        previous, following = first - timedelta(days=7), first + timedelta(days=7)
    elif mode == "day":
        first = last = anchor
        days = [anchor]
        previous, following = anchor - timedelta(days=1), anchor + timedelta(days=1)
    else:
        first, last = anchor, anchor + timedelta(days=29)
        days = [first + timedelta(days=offset) for offset in range(30)]
        previous, following = first - timedelta(days=30), first + timedelta(days=30)
    entries = calendar_entries(request.user, first, last)
    return render(request, "selection/calendar.html", {
        "active_tab": "calendar", "mode": mode, "anchor": anchor, "today": timezone.localdate(),
        "days": [{"date": day, "items": entries[day], "outside": mode == "month" and day.month != anchor.month} for day in days],
        "previous": previous, "following": following, "term": current_term(),
    })


@login_required
@student_role_required
def event_edit(request, pk=None):
    item = get_object_or_404(PersonalEvent, pk=pk, user=request.user) if pk else None
    form = PersonalEventForm(request.POST or None, instance=item, user=request.user)
    if request.method == "POST" and form.is_valid():
        event = form.save(commit=False)
        event.user = request.user
        event.save()
        form.save_m2m()
        messages.success(request, "行程已更新。" if item else "行程已新增。")
        return redirect(f"{reverse('selection:calendar')}?view=day&date={timezone.localtime(event.starts_at).date().isoformat()}")
    return render(request, "selection/event_form.html", {"form": form, "event": item, "active_tab": "calendar"}, status=400 if request.method == "POST" else 200)


@login_required
@student_role_required
@require_POST
def event_delete(request, pk):
    item = get_object_or_404(PersonalEvent, pk=pk, user=request.user)
    item.delete()
    messages.success(request, "行程已刪除。")
    return redirect("selection:calendar")
