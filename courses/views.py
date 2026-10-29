from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render

from selection.models import CustomSchedule, Selection
from selection.services import build_class_timetable, get_timetable_stats, get_user_selection_map

from .forms import OfferingFilterForm
from .models import Course, Department, EduType, Offering, StudentClass


def home(request):
    pass






    if not request.user.is_authenticated:
        return render(request, "courses/landing.html", {
            "landing_stats": {
                "classes": StudentClass.objects.count(),
                "courses": Course.objects.count(),
                "offerings": Offering.objects.count(),
            },
        })


    if request.user.is_superuser or request.user.is_admin_role:
        return redirect("admin:index")


    if request.user.is_school_role:
        if not request.path.startswith("/school/"):
            return redirect("school:dashboard")
        hot_offerings = (
            Offering.objects.annotate(
                selected_n=models.Count("selections", filter=models.Q(selections__status="selected"))
            )
            .order_by("-selected_n")
            .select_related("course")[:10]
        )
        context = {
            "active_tab": "dashboard",
            "total_edu": EduType.objects.count(),
            "total_dept": Department.objects.count(),
            "total_classes": StudentClass.objects.count(),
            "total_offering": Offering.objects.count(),
            "total_course": Course.objects.count(),
            "total_student": request.user.__class__.objects.filter(role="student").count(),
            "total_school_staff": request.user.__class__.objects.filter(role="school").count(),
            "total_selected": Selection.objects.filter(status="selected").count(),
            "hot_offerings": hot_offerings,
        }
        return render(request, "courses/home_school.html", context)


    timetable_stats = get_timetable_stats(request.user)
    enrolled_courses = (
        request.user.selections.filter(status=Selection.Status.SELECTED)
        .select_related("offering", "offering__course")
        .prefetch_related("offering__slots")
        .order_by("offering__course__name")[:6]
    )
    context = {
        "active_tab": "home",
        "timetable_stats": timetable_stats,
        "enrolled_courses": enrolled_courses,
        "total_courses": timetable_stats["total_courses"],
        "total_customs": timetable_stats["total_customs"],
        "total_credits": timetable_stats["total_credits"],
        "total_weekly_periods": timetable_stats["total_weekly_periods"],
        "today_items": timetable_stats["today_items"],
        "today_weekday": timetable_stats["today_weekday"],
        "total_offering": Offering.objects.count(),
    }
    return render(request, "courses/home_student.html", context)


@login_required
def browse(request):
    form = OfferingFilterForm(request.GET)
    qs = (
        Offering.objects.select_related("course")
        .prefetch_related("slots", "classes")
        .order_by("course__code", "serial")
        .distinct()
    )

    if form.is_valid():
        q = form.cleaned_data.get("q")
        edu = form.cleaned_data.get("edu")
        dept = form.cleaned_data.get("dept")
        grade = form.cleaned_data.get("grade")
        if q:
            qs = qs.filter(models.Q(course__name__icontains=q) | models.Q(course__code__icontains=q))
        if edu or dept or grade:
            classes = StudentClass.objects.all()
            if edu:
                classes = classes.filter(dept__edu=edu)
            if dept:
                classes = classes.filter(dept=dept)
            if grade:
                classes = [item.pk for item in classes.only("id", "name") if item.grade == grade]
                qs = qs.filter(classes__pk__in=classes)
            else:
                qs = qs.filter(classes__in=classes)

    paginator = Paginator(qs, 24)
    page_obj = paginator.get_page(request.GET.get("page"))

    page_ids = [o.id for o in page_obj.object_list]
    user_map = get_user_selection_map(request.user, page_ids) if request.user.is_student_role else {}

    group_by_edu = EduType.objects.prefetch_related("departments").order_by("code")
    get_copy = request.GET.copy()
    get_copy.pop("page", None)
    context = {
        "active_tab": "browse",
        "form": form,
        "page_obj": page_obj,
        "user_map": user_map,
        "group_by_edu": group_by_edu,
        "query_string": get_copy.urlencode(),
    }
    return render(request, "courses/browse.html", context)


@login_required
def offering_detail(request, pk):
    offering = get_object_or_404(
        Offering.objects.select_related("course").prefetch_related(
            "slots", "classes", "classes__dept", "classes__dept__edu"
        ),
        pk=pk,
    )
    my_selection = None
    if request.user.is_student_role:
        my_selection = Selection.objects.filter(user=request.user, offering=offering).first()
    context = {
        "active_tab": "browse",
        "offering": offering,
        "my_selection": my_selection,
    }
    return render(request, "courses/offering_detail.html", context)


@login_required
def class_timetables(request):
    pass
    if request.user.is_student_role:
        messages.info(request, "學生端請至「個人課表」查看每週課表，亦可在個人課表頁一鍵匯入班級課程。")
        return redirect("selection:timetable")

    all_edus = EduType.objects.all().order_by("code")
    all_depts = Department.objects.select_related("edu").order_by("code")
    all_classes = StudentClass.objects.select_related("dept", "dept__edu").order_by("dept__edu__code", "dept__code", "code")

    selected_class_id = request.GET.get("class_id")
    selected_class = None
    timetable_data = None

    if selected_class_id:
        selected_class = StudentClass.objects.filter(pk=selected_class_id).first()
    elif request.user.student_class:
        selected_class = request.user.student_class

    if selected_class:
        timetable_data = build_class_timetable(selected_class)

    context = {
        "active_tab": "class_timetables",
        "all_edus": all_edus,
        "all_depts": all_depts,
        "all_classes": all_classes,
        "selected_class": selected_class,
        "timetable": timetable_data,
    }
    return render(request, "courses/class_timetables.html", context)


@login_required
def offering_roster(request, pk):
    pass
    if not (request.user.is_school_role or request.user.is_admin_role):
        messages.error(request, "權限不足，僅學校教務人員與最高管理員可查看選課學生名冊")
        return redirect("courses:browse")
    offering = get_object_or_404(Offering.objects.select_related("course"), pk=pk)
    User = request.user.__class__
    enrolled_students = (
        User.objects.filter(selections__offering=offering, selections__status=Selection.Status.SELECTED)
        .select_related("student_class")
        .order_by("username")
    )
    context = {
        "active_tab": "browse",
        "offering": offering,
        "enrolled_students": enrolled_students,
    }
    return render(request, "courses/offering_roster.html", context)
