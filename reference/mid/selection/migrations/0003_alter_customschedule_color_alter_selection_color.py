

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('selection', '0002_alter_selection_options_selection_color_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customschedule',
            name='color',
            field=models.CharField(choices=[('terracotta', '湖水藍'), ('blue', '海灣藍'), ('green', '森林綠'), ('amber', '晴空藍'), ('purple', '晨霧藍'), ('slate', '石板藍')], default='blue', max_length=20, verbose_name='標籤顏色'),
        ),
        migrations.AlterField(
            model_name='selection',
            name='color',
            field=models.CharField(choices=[('terracotta', '湖水藍'), ('blue', '海灣藍'), ('green', '森林綠'), ('amber', '晴空藍'), ('purple', '晨霧藍'), ('slate', '石板藍')], default='terracotta', max_length=20, verbose_name='標籤顏色'),
        ),
    ]
