import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def create_current_term(apps, schema_editor):
    apps.get_model("selection", "AcademicTerm").objects.create(
        name="115 學年度第 1 學期",
        starts_on="2026-09-07",
        ends_on="2027-01-08",
        excluded_dates=["2026-09-25", "2026-09-28", "2026-10-09", "2026-10-26", "2026-12-25", "2026-12-31", "2027-01-01"],
        is_current=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_group_workspace"),
        ("selection", "0004_customschedule_import_source_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AcademicTerm",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=60, verbose_name="學期")),
                ("starts_on", models.DateField(verbose_name="開學日期")),
                ("ends_on", models.DateField(verbose_name="學期課程結束日期")),
                ("excluded_dates", models.JSONField(blank=True, default=list, verbose_name="停課日期")),
                ("is_current", models.BooleanField(default=False, verbose_name="目前學期")),
            ],
            options={"ordering": ["-starts_on"]},
        ),
        migrations.CreateModel(
            name="PersonalEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=100, verbose_name="行程名稱")),
                ("starts_at", models.DateTimeField(verbose_name="開始時間")),
                ("ends_at", models.DateTimeField(verbose_name="結束時間")),
                ("location", models.CharField(blank=True, max_length=100, verbose_name="地點")),
                ("note", models.TextField(blank=True, verbose_name="備註")),
                ("color", models.CharField(choices=[("red", "紅色"), ("orange", "橙色"), ("yellow", "黃色"), ("green", "綠色"), ("blue", "藍色"), ("indigo", "靛色"), ("purple", "紫色")], default="blue", max_length=12, verbose_name="顏色")),
                ("visibility", models.CharField(choices=[("private", "僅自己"), ("friends", "僅好友"), ("classmates", "僅同班同學"), ("groups", "指定群組")], default="private", max_length=15, verbose_name="可見範圍")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("shared_groups", models.ManyToManyField(blank=True, related_name="shared_personal_events", to="accounts.sharinggroup")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="personal_events", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["starts_at", "pk"]},
        ),
        migrations.AddConstraint(model_name="academicterm", constraint=models.CheckConstraint(condition=models.Q(ends_on__gte=models.F("starts_on")), name="academic_term_valid_dates")),
        migrations.AddConstraint(model_name="personalevent", constraint=models.CheckConstraint(condition=models.Q(ends_at__gt=models.F("starts_at")), name="personal_event_positive_duration")),
        migrations.RunPython(create_current_term, migrations.RunPython.noop),
    ]
