import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def normalize_existing_colors(apps, schema_editor):
    schedules = apps.get_model("selection", "CustomSchedule")
    for original, replacement in {"terracotta": "blue", "amber": "yellow", "slate": "indigo"}.items():
        schedules.objects.filter(color=original).update(color=replacement)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_user_share_with_classmates_user_share_with_friends_and_more'),
        ('selection', '0003_alter_customschedule_color_alter_selection_color'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='customschedule',
            name='import_source',
            field=models.CharField(choices=[('personal', '個人行程'), ('excel', 'Excel 課程')], default='personal', max_length=10),
        ),
        migrations.AddField(
            model_name='customschedule',
            name='shared_groups',
            field=models.ManyToManyField(blank=True, related_name='shared_schedules', to='accounts.sharinggroup', verbose_name='可查看的群組'),
        ),
        migrations.AddField(
            model_name='customschedule',
            name='visibility',
            field=models.CharField(choices=[('inherit', '沿用課表分享設定'), ('private', '僅自己'), ('friends', '僅好友'), ('classmates', '僅同班同學'), ('groups', '指定群組')], default='inherit', max_length=15, verbose_name='行程可見範圍'),
        ),
        migrations.AlterField(
            model_name='customschedule',
            name='color',
            field=models.CharField(choices=[('red', '紅色'), ('orange', '橙色'), ('yellow', '黃色'), ('green', '綠色'), ('blue', '藍色'), ('indigo', '靛色'), ('purple', '紫色')], default='blue', max_length=20, verbose_name='標籤顏色'),
        ),
        migrations.RunPython(normalize_existing_colors, migrations.RunPython.noop),
        migrations.CreateModel(
            name='ImportBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=160)),
                ('source', models.CharField(choices=[('class', '班級'), ('excel', 'Excel')], max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='import_batches', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='customschedule',
            name='import_batch',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='schedules', to='selection.importbatch'),
        ),
        migrations.AddField(
            model_name='selection',
            name='import_batch',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='selections', to='selection.importbatch'),
        ),
        migrations.AddConstraint(
            model_name='customschedule',
            constraint=models.UniqueConstraint(condition=models.Q(('import_source', 'excel')), fields=('user', 'title', 'weekday', 'start', 'end', 'location'), name='unique_excel_schedule'),
        ),
    ]
