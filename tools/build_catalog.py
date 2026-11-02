"""Convert Mid's public course snapshot into a database-free browser catalog."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[1]
classes, offerings, edus, depts = {}, {}, {}, {}
days = {name: n for n, name in enumerate("一二三四五六日", 1)}
for line in (root / "data/ntub/courses_raw.jsonl").read_text(encoding="utf-8").splitlines():
    rec = json.loads(line)
    cid = ":".join([rec["edu_code"], rec["dept_code"], rec["class_code"]])
    did = rec["edu_code"] + ":" + rec["dept_code"]
    edus[rec["edu_code"]] = {"id": rec["edu_code"], "name": rec["edu_name"]}
    depts[did] = {"id": did, "name": rec["dept_name"], "edu": rec["edu_code"]}
    classes[cid] = {"id": cid, "name": rec["class_name"], "code": rec["class_code"], "edu": rec["edu_code"], "dept": did}
    for s in rec.get("sessions", []):
        key = (s["課程代號"], str(s["序號"]))
        if key not in offerings:
            offerings[key] = {"id": len(offerings) + 1, "code": key[0], "serial": key[1], "name": s["課程名稱"], "teacher": s["教師"], "capacity": 40, "classes": [], "slots": []}
        course = offerings[key]
        if cid not in course["classes"]:
            course["classes"].append(cid)
        slot = {"weekday": days[s["星期"]], "period": s["節次"], "start": s["開始時間"] or "00:00", "end": s["結束時間"] or "00:00", "room": s["教室"]}
        if slot not in course["slots"]:
            course["slots"].append(slot)
for course in offerings.values():
    course["slots"].sort(key=lambda s: (s["weekday"], s["start"], s["end"]))
result = {"term": "115學年度 第1學期", "edus": list(edus.values()), "departments": list(depts.values()), "classes": list(classes.values()), "offerings": list(offerings.values())}
(root / "static/demo/catalog.json").write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print({k: len(v) for k, v in result.items() if isinstance(v, list)})
