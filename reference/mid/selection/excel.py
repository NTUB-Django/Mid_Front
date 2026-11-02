import csv
from datetime import datetime, time
from html.parser import HTMLParser
from io import BytesIO, StringIO
import re
from zipfile import ZipFile

from django.core.exceptions import ValidationError

from .forms import STANDARD_PERIOD_TIMES


MAX_BYTES = 2 * 1024 * 1024
ALIASES = {
    "title": ["課程名稱", "科目名稱", "課名", "科目", "課程", "title", "course"],
    "weekday": ["星期", "星期幾", "週幾", "上課星期", "day", "weekday"],
    "start": ["開始時間", "起始時間", "上課開始", "start"],
    "end": ["結束時間", "下課時間", "上課結束", "end"],
    "period": ["節次", "上課節次", "節數", "period"],
    "schedule": ["上課時間", "授課時間", "星期節次", "時間節次"],
    "location": ["教室", "上課教室", "地點", "上課地點", "room", "location"],
    "teacher": ["教師", "授課教師", "任課教師", "老師", "teacher"],
    "note": ["備註", "說明", "note"],
}
DAY_NAMES = {value: index for index, value in enumerate("一二三四五六日", 1)}
DAY_NAMES["天"] = 7


def text(value):
    return "" if value is None else str(value).strip()


def normalize(value):
    return re.sub(r"[\s\u3000_:：*＊()（）]", "", text(value)).lower()


class TableReader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in {"td", "th"}:
            self.cell = []
        elif tag == "br" and self.cell is not None:
            self.cell.append("\n")

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.cell is not None:
            if self.row is not None:
                self.row.append("".join(self.cell).strip())
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
            if len(self.rows) > 500:
                raise ValidationError("檔案超過 500 列，請先移除不需要的資料。")


def bounded(rows):
    result = []
    for row in rows:
        if len(result) >= 500 or len(row) > 30:
            raise ValidationError("每張工作表最多 500 列、30 欄，請先移除不需要的資料。")
        if any(len(text(value)) > 3000 for value in row):
            raise ValidationError("儲存格內容過長，請確認是課表匯出檔案。")
        result.append(list(row))
    return result


def read_tables(upload):
    if upload.size > MAX_BYTES:
        raise ValidationError("檔案不得超過 2 MB。")
    data = upload.read(MAX_BYTES + 1)
    extension = upload.name.lower().rsplit(".", 1)[-1]
    if extension not in {"xlsx", "xls", "csv"}:
        raise ValidationError("請上傳 .xlsx、.xls 或 .csv 檔案。")
    if extension == "xlsx":
        from openpyxl import load_workbook
        with ZipFile(BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 2000 or sum(item.file_size for item in entries) > 30 * 1024 * 1024:
                raise ValidationError("Excel 解壓後過大，請改用只包含課表的檔案。")
        workbook = load_workbook(BytesIO(data), read_only=True, data_only=True, keep_links=False)
        try:
            if len(workbook.worksheets) > 5:
                raise ValidationError("最多支援 5 張工作表，請只保留課表頁。")
            return [(sheet.title, bounded(sheet.iter_rows(max_row=min(sheet.max_row or 501, 501), max_col=min(sheet.max_column or 31, 31), values_only=True))) for sheet in workbook.worksheets]
        finally:
            workbook.close()
    if extension == "xls" and data.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
        import xlrd
        workbook = xlrd.open_workbook(file_contents=data, on_demand=True)
        try:
            if workbook.nsheets > 5:
                raise ValidationError("最多支援 5 張工作表。")
            tables = []
            for sheet in workbook.sheets():
                if sheet.nrows > 500 or sheet.ncols > 30:
                    raise ValidationError("每張工作表最多 500 列、30 欄。")
                rows = []
                for index in range(sheet.nrows):
                    rows.append([xlrd.xldate_as_datetime(cell.value, workbook.datemode).time() if cell.ctype == xlrd.XL_CELL_DATE else cell.value for cell in sheet.row(index)])
                tables.append((sheet.name, bounded(rows)))
            return tables
        finally:
            workbook.release_resources()
    try:
        decoded = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded = data.decode("big5")
    if extension == "xls":
        parser = TableReader()
        parser.feed(decoded)
        return [("課表", bounded(parser.rows))]
    return [("課表", bounded(csv.reader(StringIO(decoded))))]


def weekdays(value):
    raw = text(value)
    if any(marker in raw for marker in ["單週", "雙週"]):
        raise ValueError("不支援單雙週，請分開安排")
    if re.fullmatch(r"[1-7](?:\.0)?", raw):
        return [int(float(raw))]
    raw = re.sub(r"星期|禮拜|週|周", "", raw)
    values = [DAY_NAMES[part] for part in raw if part in DAY_NAMES]
    if not values:
        raise ValueError("星期需為 1–7 或週一至週日")
    return list(dict.fromkeys(values))


def clock(value):
    if isinstance(value, datetime):
        return value.time().replace(second=0, microsecond=0)
    if isinstance(value, time):
        return value.replace(second=0, microsecond=0)
    if isinstance(value, (float, int)) and 0 <= value < 1:
        minutes = round(value * 1440)
        return time(minutes // 60, minutes % 60)
    return datetime.strptime(text(value).replace("：", ":"), "%H:%M").time()


def period_times(value):
    raw = text(value)
    if re.fullmatch(r"\d+\.0", raw):
        raw = str(int(float(raw)))
    numbers = [int(number) for number in re.findall(r"\d+", raw)]
    if not numbers or min(numbers) < 1 or max(numbers) > len(STANDARD_PERIOD_TIMES):
        raise ValueError("節次需使用 1–13，例如 3-4 或 3,4")
    return STANDARD_PERIOD_TIMES[min(numbers) - 1][1], STANDARD_PERIOD_TIMES[max(numbers) - 1][2]


def entry(title, day, start, end, location="", note="", teacher=""):
    if not title or len(title) > 100:
        raise ValueError("課程名稱需為 1–100 字")
    if start >= end:
        raise ValueError("結束時間必須晚於開始時間")
    if len(location) > 60:
        raise ValueError("教室／地點不得超過 60 字")
    return {"title": title, "weekday": day, "weekday_name": "一二三四五六日"[day - 1], "start": start.strftime("%H:%M"), "end": end.strftime("%H:%M"), "location": location, "teacher": teacher, "note": note[:2000]}


def parse_table(rows):
    if not rows:
        return [], []
    candidates = []
    for index, row in enumerate(rows[:25]):
        columns = {}
        for column, value in enumerate(row):
            for key, names in ALIASES.items():
                if normalize(value) in [normalize(name) for name in names]:
                    columns.setdefault(key, column)
        if "title" in columns and ("weekday" in columns or "schedule" in columns):
            candidates.append((len(columns), index, columns))
    if candidates:
        _, header, columns = max(candidates, key=lambda item: item[0])
        parsed, errors = [], []
        for index, row in enumerate(rows[header + 1:], header + 2):
            def get(key):
                position = columns.get(key)
                return row[position] if position is not None and position < len(row) else ""
            title = text(get("title"))
            if not title:
                continue
            try:
                teacher = text(get("teacher"))
                note = " · ".join(filter(None, [teacher, text(get("note"))]))
                if "schedule" in columns and not text(get("weekday")):
                    raw = text(get("schedule"))
                    segments = re.findall(r"(?:星期|週|周|\()([一二三四五六日天])\)?\s*([^;；\n]+)", raw)
                    if not segments:
                        raise ValueError("上課時間請使用「週一 08:10-10:00」或分開的星期、節次欄")
                    for day_name, segment in segments:
                        times = re.findall(r"\d{1,2}:\d{2}", segment)
                        start, end = (clock(times[0]), clock(times[1])) if len(times) == 2 else period_times(segment)
                        parsed.append(entry(title, weekdays(day_name)[0], start, end, text(get("location")), note, teacher))
                else:
                    start, end = (clock(get("start")), clock(get("end"))) if text(get("start")) and text(get("end")) else period_times(get("period"))
                    for day in weekdays(get("weekday")):
                        parsed.append(entry(title, day, start, end, text(get("location")), note, teacher))
            except (ValueError, TypeError, IndexError):
                errors.append(f"第 {index} 列「{title[:60]}」：無法辨識星期、時間或課程內容，請檢查欄位格式。")
        return parsed, errors
    for header, row in enumerate(rows[:25]):
        days = {}
        short_day_headers = bool(row and normalize(row[0]) in {"節次", "時間", "時段"})
        for column, value in enumerate(row):
            if re.fullmatch(r"(?:星期|週|周)[一二三四五六日天]", text(value)):
                days[column] = weekdays(value)[0]
            elif column and short_day_headers and text(value) in DAY_NAMES:
                days[column] = DAY_NAMES[text(value)]
        if len(days) < 3:
            continue
        parsed, errors = [], []
        for index, row in enumerate(rows[header + 1:], header + 2):
            if not row:
                continue
            try:
                label = " ".join(text(value) for column, value in enumerate(row) if column < min(days))
                times = re.findall(r"\d{1,2}:\d{2}", label)
                start, end = (clock(times[0]), clock(times[1])) if len(times) >= 2 else period_times(label)
            except (ValueError, IndexError, TypeError):
                if any(text(row[column]) for column in days if column < len(row)):
                    errors.append(f"第 {index} 列：無法辨識左側節次或起訖時間。")
                continue
            for column, day in days.items():
                content = text(row[column]) if column < len(row) else ""
                if not content or content in {"-", "—", "無", "空堂"}:
                    continue
                lines = [line.strip() for line in content.splitlines() if line.strip()]
                try:
                    teacher = lines[1] if len(lines) > 1 else ""
                    location = lines[2] if len(lines) > 2 else ""
                    note = "\n".join([teacher, *lines[3:]]).strip()
                    parsed.append(entry(lines[0], day, start, end, location=location, note=note, teacher=teacher))
                except ValueError:
                    errors.append(f"第 {index} 列：課程名稱太長，請改用清單格式。")
        return parsed, errors
    return [], ["找不到課程欄位，請使用課程清單（課程名稱、星期、開始／結束時間或節次），或以「節次、一、二、三…」為欄的週課表。"]


def parse_upload(upload):
    try:
        tables = read_tables(upload)
    except ValidationError:
        raise
    except Exception as error:
        raise ValidationError("無法讀取此檔案，請確認沒有加密，或另存為 .xlsx／UTF-8 CSV 後重試。") from error
    parsed, errors, seen = [], [], set()
    for sheet, rows in tables:
        entries, issues = parse_table(rows)
        errors.extend(f"{sheet}：{issue}" for issue in issues)
        for item in entries:
            key = tuple(item[key] for key in ["title", "weekday", "start", "end", "location"])
            if key not in seen:
                parsed.append(item)
                seen.add(key)
    if len(parsed) > 200:
        raise ValidationError("單次最多匯入 200 個上課時段，請拆分檔案。")
    if not parsed:
        raise ValidationError(errors[:5] or ["檔案沒有可辨識的課程。"])
    return parsed, errors[:30]
