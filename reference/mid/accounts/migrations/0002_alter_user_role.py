

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('student', '學生端'), ('school', '學校端(教務/行政)'), ('admin', '最高管理員(Admin)')], default='student', max_length=20, verbose_name='角色'),
        ),
    ]
