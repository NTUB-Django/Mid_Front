from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .decorators import student_role_required
from .forms import GroupEventForm, GroupMemoForm, GroupTaskForm
from .models import GroupEvent, GroupMemo, GroupTask
from .social import member_groups


def member_group(request, pk):
    return get_object_or_404(member_groups(request.user), pk=pk)


@never_cache
@login_required
@student_role_required
def workspace(request, pk):
    group = member_group(request, pk)
    events = group.events.select_related("created_by").order_by("starts_at")[:60]
    tasks = group.tasks.select_related("created_by", "completed_by")[:100]
    memos = group.memos.select_related("created_by", "updated_by")[:30]
    return render(request, "accounts/group_workspace.html", {
        "active_tab": "connections", "group": group, "events": events, "tasks": tasks, "memos": memos,
        "event_form": GroupEventForm(), "task_form": GroupTaskForm(), "memo_form": GroupMemoForm(),
    })


@login_required
@student_role_required
@require_POST
def event_create(request, pk):
    group = member_group(request, pk)
    form = GroupEventForm(request.POST)
    if not form.is_valid():
        messages.error(request, "共同行程資料有誤，請確認名稱與開始、結束時間。")
    else:
        event = form.save(commit=False)
        event.group = group
        event.created_by = request.user
        event.save()
        messages.success(request, "共同行程已加入群組。")
    return redirect("accounts:group_workspace", pk=pk)


@never_cache
@login_required
@student_role_required
def event_edit(request, pk, item_id):
    group = member_group(request, pk)
    event = get_object_or_404(GroupEvent, pk=item_id, group=group)
    if event.created_by_id != request.user.pk and group.owner_id != request.user.pk:
        return HttpResponseForbidden("只有建立者或群組管理者可編輯這個行程。")
    form = GroupEventForm(request.POST or None, instance=event)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "共同行程已更新。")
        return redirect("accounts:group_workspace", pk=pk)
    return render(request, "accounts/group_edit.html", {"group": group, "form": form, "kind": "event", "title": "編輯共同行程"}, status=400 if request.method == "POST" else 200)


@login_required
@student_role_required
@require_POST
def event_delete(request, pk, item_id):
    group = member_group(request, pk)
    event = get_object_or_404(GroupEvent, pk=item_id, group=group)
    if event.created_by_id != request.user.pk and group.owner_id != request.user.pk:
        return HttpResponseForbidden("沒有刪除權限。")
    event.delete()
    messages.success(request, "共同行程已刪除。")
    return redirect("accounts:group_workspace", pk=pk)


@login_required
@student_role_required
@require_POST
def task_create(request, pk):
    group = member_group(request, pk)
    form = GroupTaskForm(request.POST)
    if not form.is_valid():
        messages.error(request, "請填寫待辦事項，並確認截止時間。")
    else:
        task = form.save(commit=False)
        task.group = group
        task.created_by = request.user
        task.save()
        messages.success(request, "共同待辦已加入。")
    return redirect("accounts:group_workspace", pk=pk)


@login_required
@student_role_required
@require_POST
def task_toggle(request, pk, item_id):
    group = member_group(request, pk)
    task = get_object_or_404(GroupTask, pk=item_id, group=group)
    task.completed = not task.completed
    task.completed_by = request.user if task.completed else None
    task.save(update_fields=["completed", "completed_by"])
    return redirect("accounts:group_workspace", pk=pk)


@login_required
@student_role_required
@require_POST
def task_delete(request, pk, item_id):
    group = member_group(request, pk)
    task = get_object_or_404(GroupTask, pk=item_id, group=group)
    if task.created_by_id != request.user.pk and group.owner_id != request.user.pk:
        return HttpResponseForbidden("沒有刪除權限。")
    task.delete()
    return redirect("accounts:group_workspace", pk=pk)


@login_required
@student_role_required
@require_POST
def memo_create(request, pk):
    group = member_group(request, pk)
    form = GroupMemoForm(request.POST)
    if not form.is_valid():
        messages.error(request, "備忘標題與內容都必須填寫。")
    else:
        memo = form.save(commit=False)
        memo.group = group
        memo.created_by = request.user
        memo.updated_by = request.user
        memo.save()
        messages.success(request, "團體備忘已建立。")
    return redirect("accounts:group_workspace", pk=pk)


@never_cache
@login_required
@student_role_required
def memo_edit(request, pk, item_id):
    group = member_group(request, pk)
    memo = get_object_or_404(GroupMemo, pk=item_id, group=group)
    form = GroupMemoForm(request.POST or None, instance=memo)
    if request.method == "POST" and form.is_valid():
        memo = form.save(commit=False)
        memo.updated_by = request.user
        memo.save()
        messages.success(request, "團體備忘已更新。")
        return redirect("accounts:group_workspace", pk=pk)
    return render(request, "accounts/group_edit.html", {"group": group, "form": form, "kind": "memo", "title": "編輯團體備忘"}, status=400 if request.method == "POST" else 200)


@login_required
@student_role_required
@require_POST
def memo_delete(request, pk, item_id):
    group = member_group(request, pk)
    memo = get_object_or_404(GroupMemo, pk=item_id, group=group)
    if memo.created_by_id != request.user.pk and group.owner_id != request.user.pk:
        return HttpResponseForbidden("沒有刪除權限。")
    memo.delete()
    return redirect("accounts:group_workspace", pk=pk)
