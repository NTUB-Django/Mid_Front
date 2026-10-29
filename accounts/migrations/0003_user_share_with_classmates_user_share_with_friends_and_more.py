import django.db.models.deletion
import django.db.models.functions.text
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_alter_user_role'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('courses', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='share_with_classmates',
            field=models.BooleanField(default=True, verbose_name='分享給同班同學'),
        ),
        migrations.AddField(
            model_name='user',
            name='share_with_friends',
            field=models.BooleanField(default=False, verbose_name='分享給好友'),
        ),
        migrations.AddField(
            model_name='user',
            name='timetable_public',
            field=models.BooleanField(default=False, verbose_name='公開給所有登入學生'),
        ),
        migrations.CreateModel(
            name='Friendship',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('accepted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('requested_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_friendships', to=settings.AUTH_USER_MODEL)),
                ('user_high', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='friendships_high', to=settings.AUTH_USER_MODEL)),
                ('user_low', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='friendships_low', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='SharingGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=60, verbose_name='群組名稱')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owned_sharing_groups', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='GroupMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('accepted', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sharing_memberships', to=settings.AUTH_USER_MODEL)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='accounts.sharinggroup')),
            ],
        ),
        migrations.AddField(
            model_name='user',
            name='timetable_shared_groups',
            field=models.ManyToManyField(blank=True, related_name='sharing_users', to='accounts.sharinggroup', verbose_name='分享課表的群組'),
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.UniqueConstraint(django.db.models.functions.text.Lower('email'), condition=models.Q(('email', ''), _negated=True), name='unique_user_email_ci'),
        ),
        migrations.AddConstraint(
            model_name='friendship',
            constraint=models.UniqueConstraint(fields=('user_low', 'user_high'), name='unique_friend_pair'),
        ),
        migrations.AddConstraint(
            model_name='friendship',
            constraint=models.CheckConstraint(condition=models.Q(('user_low__lt', models.F('user_high'))), name='ordered_friend_pair'),
        ),
        migrations.AddConstraint(
            model_name='friendship',
            constraint=models.CheckConstraint(condition=models.Q(('requested_by', models.F('user_low')), ('requested_by', models.F('user_high')), _connector='OR'), name='friend_request_from_pair'),
        ),
        migrations.AddConstraint(
            model_name='groupmembership',
            constraint=models.UniqueConstraint(fields=('group', 'user'), name='unique_group_member'),
        ),
    ]
