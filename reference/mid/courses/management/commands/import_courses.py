from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from courses.models import Course, Department, EduType, Offering, OfferingSlot, StudentClass
from selection.models import Selection

WEEKDAY_MAP = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7}


class Command(BaseCommand):
    help = "將爬蟲取得的 data/ntub/courses_raw.jsonl 批次匯入資料庫"

    def add_arguments(self, parser):
        parser.add_argument("--file", default="data/ntub/courses_raw.jsonl", help="JSONL 檔案路徑")
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument("--reset", action="store_true", help="先清空既有課程資料再匯入")
        mode.add_argument("--if-empty", action="store_true", help="資料庫尚無開課資料時才匯入")

    @transaction.atomic
    def handle(self, *args, **opts):
        import json
        import os

        from django.conf import settings

        if opts.get("if_empty"):
            if connection.vendor == "postgresql":
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_advisory_xact_lock(%s)", [6718234])
            if Offering.objects.exists():
                self.stdout.write("資料庫已有開課資料，略過首次匯入。")
                return

        path = opts["file"]
        if not os.path.isabs(path):
            path = os.path.join(settings.BASE_DIR, path)
        if not os.path.exists(path):
            raise CommandError(f"找不到檔案: {path}")

        if opts["reset"]:
            self.stdout.write("清空既有資料…")
            Selection.objects.all().delete()
            OfferingSlot.objects.all().delete()
            Offering.classes.through.objects.all().delete()
            Offering.objects.all().delete()
            Course.objects.all().delete()
            StudentClass.objects.all().delete()
            Department.objects.all().delete()
            EduType.objects.all().delete()

        edu_cache = {}
        dept_cache = {}
        cls_cache = {}
        course_cache = {}
        offering_cache = {}
        slot_keys = set()
        class_links = set()

        rows = 0
        failed = 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                rows += 1
                if not rec.get("query_ok"):
                    failed += 1

                edu = edu_cache.get(rec["edu_code"])
                if edu is None:
                    edu, _ = EduType.objects.get_or_create(code=rec["edu_code"], defaults={"name": rec["edu_name"]})
                    edu_cache[rec["edu_code"]] = edu

                dkey = (rec["edu_code"], rec["dept_code"])
                dept = dept_cache.get(dkey)
                if dept is None:
                    dept, _ = Department.objects.get_or_create(
                        edu=edu, code=rec["dept_code"], defaults={"name": rec["dept_name"]}
                    )
                    dept_cache[dkey] = dept

                ckey = (rec["edu_code"], rec["dept_code"], rec["class_code"])
                cls = cls_cache.get(ckey)
                if cls is None:
                    cls, _ = StudentClass.objects.get_or_create(
                        dept=dept, code=rec["class_code"], defaults={"name": rec["class_name"]}
                    )
                    cls_cache[ckey] = cls

                for s in rec.get("sessions", []):
                    course = course_cache.get(s["課程代號"])
                    if course is None:
                        course, _ = Course.objects.get_or_create(code=s["課程代號"], defaults={"name": s["課程名稱"]})
                        course_cache[s["課程代號"]] = course

                    okey = (course.id, s["序號"])
                    offering = offering_cache.get(okey)
                    if offering is None:
                        offering, _ = Offering.objects.get_or_create(
                            course=course, serial=s["序號"], defaults={"teacher": s["教師"], "capacity": 40}
                        )
                        offering_cache[okey] = offering

                    class_links.add((offering.id, cls.id))
                    weekday = WEEKDAY_MAP.get(s["星期"])
                    if weekday is None:
                        self.stderr.write(f"未知星期: {s['星期']} ({s['課程名稱']})")
                        continue
                    slot_keys.add(
                        (offering.id, weekday, s["節次"], s["開始時間"] or "00:00", s["結束時間"] or "00:00", s["教室"])
                    )

        OfferingSlot.objects.bulk_create(
            [
                OfferingSlot(offering_id=o, weekday=w, period=p, start=st, end=en, room=r)
                for o, w, p, st, en, r in slot_keys
            ],
            ignore_conflicts=True,
            batch_size=500,
        )
        Offering.classes.through.objects.bulk_create(
            [Offering.classes.through(offering_id=o, studentclass_id=c) for o, c in class_links],
            ignore_conflicts=True,
            batch_size=500,
        )

        self.stdout.write(self.style.SUCCESS(
            f"匯入完成：處理 {rows} 筆班級紀錄，"
            f"學制 {EduType.objects.count()} / 系所 {Department.objects.count()} / 班級 {StudentClass.objects.count()} / "
            f"課程 {Course.objects.count()} / 開課 {Offering.objects.count()} / 時段 {OfferingSlot.objects.count()}"
        ))
        if failed:
            self.stderr.write(f"注意：有 {failed} 筆班級查詢失敗（未抓到課程）。")
