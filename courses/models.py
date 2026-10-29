import re
import unicodedata

from django.db import models


class EduType(models.Model):
    code = models.CharField("學制代碼", max_length=10, primary_key=True)
    name = models.CharField("學制名稱", max_length=40)

    class Meta:
        verbose_name = "學制"
        verbose_name_plural = "學制"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} {self.name}"


class Department(models.Model):
    edu = models.ForeignKey(EduType, on_delete=models.CASCADE, verbose_name="學制", related_name="departments")
    code = models.CharField("系所代碼", max_length=10)
    name = models.CharField("系所名稱", max_length=60)

    class Meta:
        verbose_name = "系所"
        verbose_name_plural = "系所"
        ordering = ["edu", "code"]
        constraints = [models.UniqueConstraint(fields=["edu", "code"], name="uniq_dept_edu_code")]

    def __str__(self):
        return f"{self.edu.name} {self.name}"


class StudentClass(models.Model):
    dept = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name="系所", related_name="classes")
    code = models.CharField("班級代碼", max_length=20)
    name = models.CharField("班級名稱", max_length=60)

    class Meta:
        verbose_name = "班級"
        verbose_name_plural = "班級"
        ordering = ["dept", "code"]
        constraints = [models.UniqueConstraint(fields=["dept", "code"], name="uniq_class_dept_code")]

    def __str__(self):
        return f"{self.dept.name} {self.name}"

    @property
    def full_name(self) -> str:
        return f"{self.dept.edu.name} {self.dept.name} {self.name}"

    @property
    def grade(self):
        match = re.search(r"([一二三四五六七八九1-9])(?:年|(?=[甲乙丙丁戊己庚辛壬癸]))", unicodedata.normalize("NFKC", self.name))
        if not match:
            return None
        value = match.group(1)
        return int(value) if value.isdigit() else "一二三四五六七八九".index(value) + 1


class Course(models.Model):
    code = models.CharField("課程代號", max_length=20, unique=True)
    name = models.CharField("課程名稱", max_length=120, db_index=True)

    class Meta:
        verbose_name = "課程"
        verbose_name_plural = "課程"
        ordering = ["code"]

    def __str__(self):
        return f"{self.name}（{self.code}）"


class Offering(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="課程", related_name="offerings")
    serial = models.CharField("序號", max_length=10)
    teacher = models.CharField("教師", max_length=60, blank=True)
    capacity = models.PositiveIntegerField("名額", default=40)
    classes = models.ManyToManyField(StudentClass, verbose_name="開課班級", related_name="offerings", blank=True)

    class Meta:
        verbose_name = "開課班別"
        verbose_name_plural = "開課班別"
        ordering = ["course__code", "serial"]
        constraints = [models.UniqueConstraint(fields=["course", "serial"], name="uniq_offering_course_serial")]

    def __str__(self):
        return f"{self.course.name}（{self.course.code}-{self.serial}）"

    @property
    def display_name(self) -> str:
        return f"{self.course.name} 序{self.serial}"

    @property
    def pre_count(self) -> int:
        return self.selections.filter(status="pre").count()

    @property
    def selected_count(self) -> int:
        return self.selections.filter(status="selected").count()

    def slots_summary(self) -> str:
        return "、".join(str(sl) for sl in self.slots.all())


class OfferingSlot(models.Model):
    WEEKDAY_CHOICES = [
        (1, "一"),
        (2, "二"),
        (3, "三"),
        (4, "四"),
        (5, "五"),
        (6, "六"),
        (7, "日"),
    ]

    offering = models.ForeignKey(Offering, on_delete=models.CASCADE, verbose_name="開課", related_name="slots")
    weekday = models.PositiveSmallIntegerField("星期", choices=WEEKDAY_CHOICES, db_index=True)
    period = models.CharField("節次", max_length=20)
    start = models.TimeField("開始時間")
    end = models.TimeField("結束時間")
    room = models.CharField("教室", max_length=40, blank=True)

    class Meta:
        verbose_name = "上課時段"
        verbose_name_plural = "上課時段"
        ordering = ["weekday", "start"]
        constraints = [models.UniqueConstraint(fields=["offering", "weekday", "period"], name="uniq_slot_offering_wd_period")]

    def __str__(self):
        return f"星期{self.get_weekday_display()} {self.period}（{self.start:%H:%M}-{self.end:%H:%M}）{self.room}"
