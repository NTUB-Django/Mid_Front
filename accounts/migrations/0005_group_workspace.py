import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_user_email_verified_at"),
    ]

    operations = [
        migrations.CreateModel(
            name="GroupEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=100)),
                ("starts_at", models.DateTimeField()),
                ("ends_at", models.DateTimeField()),
                ("location", models.CharField(blank=True, max_length=100)),
                ("note", models.TextField(blank=True)),
                ("color", models.CharField(default="blue", max_length=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="created_group_events", to=settings.AUTH_USER_MODEL)),
                ("group", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="accounts.sharinggroup")),
            ],
            options={"ordering": ["starts_at", "pk"]},
        ),
        migrations.CreateModel(
            name="GroupTask",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=160)),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("completed", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="completed_group_tasks", to=settings.AUTH_USER_MODEL)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="created_group_tasks", to=settings.AUTH_USER_MODEL)),
                ("group", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tasks", to="accounts.sharinggroup")),
            ],
            options={"ordering": ["completed", "due_at", "created_at"]},
        ),
        migrations.CreateModel(
            name="GroupMemo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=100)),
                ("body", models.TextField()),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="created_group_memos", to=settings.AUTH_USER_MODEL)),
                ("group", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memos", to="accounts.sharinggroup")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="updated_group_memos", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-updated_at", "-pk"]},
        ),
    ]
