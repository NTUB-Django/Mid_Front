from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .decorators import student_role_required
from .forms import SharingGroupForm, TimetablePrivacyForm
from .models import Friendship, GroupMembership, SharingGroup, User
from .social import can_view_timetable, friend_ids, member_groups, people_rows


@never_cache
@login_required
@student_role_required
def connections(request):
    return _render_connections(request)


def _render_connections(request, privacy_form=None, group_form=None, status=200):
    user = request.user
    students = User.objects.filter(role=User.Role.STUDENT, is_active=True).exclude(pk=user.pk).select_related("student_class", "student_class__dept")
    classmates = students.filter(student_class_id=user.student_class_id) if user.student_class_id else students.none()
    friends = students.filter(pk__in=friend_ids(user)).order_by("username")
    pairs = Friendship.objects.filter(Q(user_low=user) | Q(user_high=user)).select_related("user_low", "user_high", "requested_by").order_by("-created_at")
    incoming, outgoing, accepted = [], [], []
    for pair in pairs:
        row = {"relation": pair, "person": pair.other_user(user)}
        if pair.accepted:
            accepted.append(row)
        elif pair.requested_by_id == user.pk:
            outgoing.append(row)
        else:
            incoming.append(row)
    query = request.GET.get("q", "").strip()[:150]
    search_result = students.filter(username=query).first() if query else None
    search_relation = None
    if search_result:
        search_relation = next((p for p in pairs if p.other_user(user).pk == search_result.pk), None)
    groups = []
    for group in member_groups(user).select_related("owner").prefetch_related("memberships__user").order_by("name", "pk"):
        memberships = list(group.memberships.all())
        for membership in memberships:
            membership.can_view = membership.accepted and can_view_timetable(user, membership.user)
        current_ids = [member.user_id for member in memberships]
        groups.append({"group": group, "memberships": memberships, "invitees": friends.exclude(pk__in=current_ids).exclude(pk=group.owner_id), "is_owner": group.owner_id == user.pk, "owner_can_view": can_view_timetable(user, group.owner)})
    return render(request, "accounts/connections.html", {
        "active_tab": "connections", "privacy_form": privacy_form if privacy_form is not None else TimetablePrivacyForm(instance=user),
        "group_form": group_form if group_form is not None else SharingGroupForm(),
        "classmates": people_rows(user, classmates.order_by("username")), "friends": people_rows(user, friends),
        "incoming": incoming, "outgoing": outgoing, "accepted": accepted,
        "q": query, "search_result": search_result, "search_relation": search_relation, "groups": groups,
        "group_invitations": user.sharing_memberships.filter(accepted=False).select_related("group", "group__owner"),
    }, status=status)


@never_cache
@login_required
@student_role_required
@require_POST
def privacy(request):
    form = TimetablePrivacyForm(request.POST, instance=request.user)
    if not form.is_valid():
        return _render_connections(request, privacy_form=form, status=400)
    form.save()
    messages.success(request, "課表分享權限已更新；取消分享後即停止授權。")
    return redirect("accounts:connections")


@login_required
@student_role_required
@require_POST
def friend_request(request):
    target = get_object_or_404(User, username=request.POST.get("username", "").strip(), role=User.Role.STUDENT, is_active=True)
    if target.pk == request.user.pk:
        return HttpResponseBadRequest("無法邀請自己。")
    low, high = sorted([request.user.pk, target.pk])
    pair, created = Friendship.objects.get_or_create(user_low_id=low, user_high_id=high, defaults={"requested_by": request.user})
    messages.info(request, "好友邀請已送出。" if created else "已有好友關係或待處理邀請，請在邀請區處理。")
    return redirect("accounts:connections")


@login_required
@student_role_required
@require_POST
def friend_action(request, pk, action):
    pair = get_object_or_404(Friendship.objects.filter(Q(user_low=request.user) | Q(user_high=request.user)), pk=pk)
    if action == "accept":
        if pair.accepted or pair.requested_by_id == request.user.pk:
            return HttpResponseBadRequest("只能接受對方送來的待處理邀請。")
        pair.accepted = True
        pair.save(update_fields=["accepted"])
        messages.success(request, "已成為好友。是否分享課表，仍依個人設定。")
    elif action == "remove":
        pair.delete()
        messages.success(request, "已移除好友關係或邀請；群組分享需另外調整。")
    else:
        return HttpResponseBadRequest("無效的操作。")
    return redirect("accounts:connections")


@never_cache
@login_required
@student_role_required
@require_POST
def group_create(request):
    form = SharingGroupForm(request.POST)
    if not form.is_valid():
        return _render_connections(request, group_form=form, status=400)
    group = form.save(commit=False)
    group.owner = request.user
    group.save()
    messages.success(request, "群組已建立，可邀請好友。加入群組不會自動公開自己的課表。")
    return redirect("accounts:connections")


@login_required
@student_role_required
@require_POST
def group_invite(request, pk):
    group = get_object_or_404(SharingGroup, pk=pk, owner=request.user)
    target = get_object_or_404(User, username=request.POST.get("username", ""), pk__in=friend_ids(request.user), role=User.Role.STUDENT, is_active=True)
    if target.pk == group.owner_id:
        return HttpResponseBadRequest("群組建立者已是成員。")
    GroupMembership.objects.get_or_create(group=group, user=target)
    messages.success(request, "群組邀請已送出，須由對方接受。")
    return redirect("accounts:connections")


@login_required
@student_role_required
@require_POST
def membership_action(request, pk, action):
    membership = get_object_or_404(GroupMembership.objects.select_related("group", "user"), pk=pk)
    is_self = membership.user_id == request.user.pk
    if action == "accept" and is_self and not membership.accepted:
        membership.accepted = True
        membership.save(update_fields=["accepted"])
        messages.success(request, "已加入群組。若要分享自己的課表，請另外勾選此群組。")
    elif action == "remove" and (is_self or membership.group.owner_id == request.user.pk):
        membership.user.timetable_shared_groups.remove(membership.group)
        membership.delete()
        messages.success(request, "已退出、拒絕邀請或移除成員，該成員的群組分享權限已撤回。")
    else:
        return HttpResponseBadRequest("沒有權限執行這項操作。")
    return redirect("accounts:connections")


@login_required
@student_role_required
@require_POST
def group_delete(request, pk):
    group = get_object_or_404(SharingGroup, pk=pk, owner=request.user)
    group.delete()
    messages.success(request, "群組已解散，透過此群組的課表分享權限已撤回。")
    return redirect("accounts:connections")
