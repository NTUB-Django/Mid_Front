from accounts.social import can_view_timetable, friend_ids, member_groups

from .models import CustomSchedule


def visible_schedules(owner, viewer=None):
    schedules = owner.custom_schedules.prefetch_related("shared_groups")
    if viewer is None or viewer.pk == owner.pk:
        return schedules
    if not can_view_timetable(viewer, owner):
        return schedules.none()
    friendship = owner.pk in friend_ids(viewer)
    same_class = bool(owner.student_class_id and owner.student_class_id == viewer.student_class_id)
    shared = set(member_groups(owner).values_list("pk", flat=True)) & set(member_groups(viewer).values_list("pk", flat=True))
    allowed = []
    for schedule in schedules:
        visibility = schedule.visibility
        if visibility == CustomSchedule.Visibility.INHERIT or visibility == CustomSchedule.Visibility.FRIENDS and friendship or visibility == CustomSchedule.Visibility.CLASSMATES and same_class or visibility == CustomSchedule.Visibility.GROUPS and any(group.pk in shared for group in schedule.shared_groups.all()):
            allowed.append(schedule.pk)
    return schedules.filter(pk__in=allowed)
