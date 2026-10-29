from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0005_group_workspace")]

    operations = [
        migrations.AddField(model_name="user", name="avatar", field=models.ImageField(blank=True, upload_to="avatars/", verbose_name="頭像")),
        migrations.AddField(model_name="user", name="profile_public", field=models.BooleanField(default=False, verbose_name="公開基本資料")),
    ]
