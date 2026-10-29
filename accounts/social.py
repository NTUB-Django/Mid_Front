from django.db.models import Q

from .models import Friendship, SharingGroup, User


def friend_ids(user):
    pairs = Friendship.objects.filter(Q(user_low=user) | Q(user_high=user), accepted=True)
    return [high if low == user.pk else low for low, high in pairs.values_list("user_low_id", "user_high_id")]


def member_groups(user):
    return SharingGroup.objects.filter(Q(owner=user) | Q(memberships__user=user, memberships__accepted=True)).distinct()


def can_view_timetable(viewer, owner):
    if not viewer.is_authenticated or not viewer.is_active or not owner.is_active:
        return False
    if viewer.pk == owner.pk:
        return True
    if viewer.role != User.Role.STUDENT or owner.role != User.Role.STUDENT:
        return False
    if owner.timetable_public:
        return True
    if owner.share_with_classmates and owner.student_class_id and owner.student_class_id == viewer.student_class_id:
        return True
    if owner.share_with_friends and owner.pk in friend_ids(viewer):
        return True
    return owner.timetable_shared_groups.filter(pk__in=member_groups(owner).values("pk")).filter(pk__in=member_groups(viewer).values("pk")).exists()


def people_rows(viewer, users):
    return [{"person": person, "can_view": can_view_timetable(viewer, person)} for person in users]
