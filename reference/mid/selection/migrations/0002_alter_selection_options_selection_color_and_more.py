

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('selection', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='selection',
            options={'ordering': ['created_at'], 'verbose_name': '個人課表課程', 'verbose_name_plural': '個人課表課程'},
        ),
        migrations.AddField(
            model_name='selection',
            name='color',
            field=models.CharField(choices=[('terracotta', '陶土紅'), ('blue', '靛青藍'), ('green', '草木綠'), ('amber', '琥珀黃'), ('purple', '丁香紫'), ('slate', '石墨灰')], default='terracotta', max_length=20, verbose_name='標籤顏色'),
        ),
        migrations.AddField(
            model_name='selection',
            name='notes',
            field=models.CharField(blank=True, max_length=100, verbose_name='個人備註'),
        ),
        migrations.AlterField(
            model_name='selection',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='加入時間'),
        ),
        migrations.AlterField(
            model_name='selection',
            name='status',
            field=models.CharField(choices=[('pre', '預選中'), ('selected', '正取'), ('rejected', '未選上')], db_index=True, default='selected', max_length=20, verbose_name='狀態'),
        ),
        migrations.CreateModel(
            name='CustomSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100, verbose_name='行程名稱')),
                ('weekday', models.PositiveSmallIntegerField(choices=[(1, '星期一'), (2, '星期二'), (3, '星期三'), (4, '星期四'), (5, '星期五'), (6, '星期六'), (7, '星期日')], db_index=True, verbose_name='星期')),
                ('period', models.CharField(blank=True, max_length=30, verbose_name='節次名稱')),
                ('start', models.TimeField(verbose_name='開始時間')),
                ('end', models.TimeField(verbose_name='結束時間')),
                ('location', models.CharField(blank=True, max_length=60, verbose_name='地點/教室')),
                ('color', models.CharField(choices=[('terracotta', '陶土紅'), ('blue', '靛青藍'), ('green', '草木綠'), ('amber', '琥珀黃'), ('purple', '丁香紫'), ('slate', '石墨灰')], default='blue', max_length=20, verbose_name='標籤顏色')),
                ('note', models.TextField(blank=True, verbose_name='備註說明')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='建立時間')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新時間')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='custom_schedules', to=settings.AUTH_USER_MODEL, verbose_name='使用者')),
            ],
            options={
                'verbose_name': '個人自訂行程',
                'verbose_name_plural': '個人自訂行程',
                'ordering': ['weekday', 'start'],
            },
        ),
    ]
