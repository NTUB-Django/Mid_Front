

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=20, unique=True, verbose_name='課程代號')),
                ('name', models.CharField(db_index=True, max_length=120, verbose_name='課程名稱')),
            ],
            options={
                'verbose_name': '課程',
                'verbose_name_plural': '課程',
                'ordering': ['code'],
            },
        ),
        migrations.CreateModel(
            name='EduType',
            fields=[
                ('code', models.CharField(max_length=10, primary_key=True, serialize=False, verbose_name='學制代碼')),
                ('name', models.CharField(max_length=40, verbose_name='學制名稱')),
            ],
            options={
                'verbose_name': '學制',
                'verbose_name_plural': '學制',
                'ordering': ['code'],
            },
        ),
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=10, verbose_name='系所代碼')),
                ('name', models.CharField(max_length=60, verbose_name='系所名稱')),
                ('edu', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='departments', to='courses.edutype', verbose_name='學制')),
            ],
            options={
                'verbose_name': '系所',
                'verbose_name_plural': '系所',
                'ordering': ['edu', 'code'],
            },
        ),
        migrations.CreateModel(
            name='Offering',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('serial', models.CharField(max_length=10, verbose_name='序號')),
                ('teacher', models.CharField(blank=True, max_length=60, verbose_name='教師')),
                ('capacity', models.PositiveIntegerField(default=40, verbose_name='名額')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='offerings', to='courses.course', verbose_name='課程')),
            ],
            options={
                'verbose_name': '開課班別',
                'verbose_name_plural': '開課班別',
                'ordering': ['course__code', 'serial'],
            },
        ),
        migrations.CreateModel(
            name='OfferingSlot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('weekday', models.PositiveSmallIntegerField(choices=[(1, '一'), (2, '二'), (3, '三'), (4, '四'), (5, '五'), (6, '六'), (7, '日')], db_index=True, verbose_name='星期')),
                ('period', models.CharField(max_length=20, verbose_name='節次')),
                ('start', models.TimeField(verbose_name='開始時間')),
                ('end', models.TimeField(verbose_name='結束時間')),
                ('room', models.CharField(blank=True, max_length=40, verbose_name='教室')),
                ('offering', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='slots', to='courses.offering', verbose_name='開課')),
            ],
            options={
                'verbose_name': '上課時段',
                'verbose_name_plural': '上課時段',
                'ordering': ['weekday', 'start'],
            },
        ),
        migrations.CreateModel(
            name='StudentClass',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=20, verbose_name='班級代碼')),
                ('name', models.CharField(max_length=60, verbose_name='班級名稱')),
                ('dept', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='classes', to='courses.department', verbose_name='系所')),
            ],
            options={
                'verbose_name': '班級',
                'verbose_name_plural': '班級',
                'ordering': ['dept', 'code'],
            },
        ),
        migrations.AddField(
            model_name='offering',
            name='classes',
            field=models.ManyToManyField(blank=True, related_name='offerings', to='courses.studentclass', verbose_name='開課班級'),
        ),
        migrations.AddConstraint(
            model_name='department',
            constraint=models.UniqueConstraint(fields=('edu', 'code'), name='uniq_dept_edu_code'),
        ),
        migrations.AddConstraint(
            model_name='offeringslot',
            constraint=models.UniqueConstraint(fields=('offering', 'weekday', 'period'), name='uniq_slot_offering_wd_period'),
        ),
        migrations.AddConstraint(
            model_name='studentclass',
            constraint=models.UniqueConstraint(fields=('dept', 'code'), name='uniq_class_dept_code'),
        ),
        migrations.AddConstraint(
            model_name='offering',
            constraint=models.UniqueConstraint(fields=('course', 'serial'), name='uniq_offering_course_serial'),
        ),
    ]
