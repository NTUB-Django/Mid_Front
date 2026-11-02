from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from courses.models import StudentClass


class Command(BaseCommand):
    help = "建立本機期中展示帳號，不覆蓋已存在帳號的密碼與資料"

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('示範帳號僅能在本機開發模式建立。')
        student_class = StudentClass.objects.filter(dept__code='401', name__contains='一年甲班').first()
        student_class = student_class or StudentClass.objects.order_by('pk').first()
        accounts = [
            ('admin', 'admin1234', User.Role.ADMIN, '展示管理員'),
            ('school', 'school123', User.Role.SCHOOL, '展示教務人員'),
            ('student', 'student123', User.Role.STUDENT, '展示學生'),
        ]
        for username, password, role, display_name in accounts:
            if User.objects.filter(username=username).exists():
                self.stdout.write(f'{username} 已存在，保留原有密碼、角色與課表。')
                continue
            user = User(username=username, role=role, display_name=display_name,
                        email=f'{username}@example.com',
                        student_class=student_class if role == User.Role.STUDENT else None)
            user.set_password(password)
            user.save()
            self.stdout.write(f'已建立本機展示帳號：{username} / {password}')
        self.stdout.write(self.style.SUCCESS('示範帳號準備完成。這些公開密碼僅供本機展示。'))
