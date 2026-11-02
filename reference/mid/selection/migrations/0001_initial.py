

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('courses', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Selection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pre', '預選中'), ('selected', '正取'), ('rejected', '未選上')], db_index=True, default='pre', max_length=20, verbose_name='狀態')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='預選時間')),
                ('offering', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='selections', to='courses.offering', verbose_name='開課')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='selections', to=settings.AUTH_USER_MODEL, verbose_name='使用者')),
            ],
            options={
                'verbose_name': '選課紀錄',
                'verbose_name_plural': '選課紀錄',
                'ordering': ['created_at'],
                'constraints': [models.UniqueConstraint(fields=('user', 'offering'), name='uniq_selection_user_offering')],
            },
        ),
    ]
