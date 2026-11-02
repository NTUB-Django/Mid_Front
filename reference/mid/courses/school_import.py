from io import BytesIO
import re
import secrets
import time

from django import forms
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from accounts.forms import validate_login_email
from accounts.models import User
from courses.models import StudentClass
from selection.excel import normalize, read_tables, text

from .school_views import school_required


HEADERS = {
    "username": {"學號", "學生學號", "studentid", "studentnumber"},
    "email": {"email", "電子郵件", "電子信箱", "信箱", "郵件"},
    "display_name": {"姓名", "學生姓名", "顯示名稱", "name"},
    "department": {"系所代碼", "系代碼", "departmentcode", "dept"},
    "student_class": {"班級代碼", "班級", "classcode", "class"},
    "password": {"初始密碼", "密碼", "initialpassword", "password"},
}


def parse_students(upload):
    result = []
    errors = []
    seen_names = set()
    seen_emails = set()
    try:
        tables = read_tables(upload)
    except ValidationError:
        raise
    except Exception as error:
        raise ValidationError("無法讀取此檔案，請另存為 .xlsx 或 UTF-8 CSV 後重試。") from error
    for sheet_name, table in tables:
        header_index = None
        columns = {}
        for index, values in enumerate(table[:20]):
            candidate = {}
            for column, value in enumerate(values):
                for key, aliases in HEADERS.items():
                    if normalize(value) in aliases:
                        candidate[key] = column
            if "username" in candidate and "email" in candidate:
                columns = candidate
                header_index = index
                break
        if header_index is None:
            continue
        for row_index, values in enumerate(table[header_index + 1:], header_index + 2):
            def cell(key):
                column = columns.get(key)
                return text(values[column]) if column is not None and column < len(values) else ""
            username = cell("username")
            if re.fullmatch(r"\d+\.0", username):
                username = str(int(float(username)))
            email = cell("email")
            if not username and not email and not any(text(value) for value in values):
                continue
            label = f"{sheet_name} 第 {row_index} 列"
            try:
                if not re.fullmatch(r"[A-Za-z0-9_-]{3,30}", username) or username.lower() == "admin":
                    raise ValidationError("學號須為 3–30 個英數字、底線或連字號，且不可使用 admin。")
                existing = User.objects.filter(username__iexact=username).first()
                if existing and existing.role != User.Role.STUDENT:
                    raise ValidationError("此學號屬於管理帳號，不可匯入。")
                email = validate_login_email(forms.EmailField().clean(email), existing)
                if username.lower() in seen_names or email in seen_emails:
                    raise ValidationError("同一份檔案有重複學號或 Email。")
                seen_names.add(username.lower())
                seen_emails.add(email)
                department = cell("department")
                class_code = cell("student_class")
                student_class = None
                if department or class_code:
                    if not department or not class_code:
                        raise ValidationError("班級資料須同時填入系所代碼與班級代碼。")
                    matches = StudentClass.objects.filter(dept__code=department, code=class_code)[:2]
                    if len(matches) != 1:
                        raise ValidationError("找不到唯一對應的系所與班級代碼。")
                    student_class = matches[0]
                password = cell("password")
                if not existing:
                    if not password:
                        raise ValidationError("新學生必須提供初始密碼。")
                    candidate = User(username=username, email=email)
                    validate_password(password, user=candidate)
                result.append({
                    "username": username,
                    "email": email,
                    "display_name": cell("display_name")[:60],
                    "student_class_id": student_class.pk if student_class else None,
                    "student_class_name": student_class.full_name if student_class else "",
                    "password_hash": make_password(password) if not existing else None,
                    "existing_id": existing.pk if existing else None,
                    "action": "更新" if existing else "建立",
                })
            except (ValidationError, forms.ValidationError) as error:
                errors.append(f"{label}：{'；'.join(error.messages)}")
            if len(result) > 200:
                raise ValidationError("每次最多匯入 200 位學生。")
    if not result and not errors:
        raise ValidationError("找不到含有「學號」和「Email」欄位的學生資料。")
    return result, errors


@school_required
def student_import(request):
    context = {"active_tab": "student_import"}
    if request.method == "POST":
        request.session.pop("student_import_preview", None)
        upload = request.FILES.get("file")
        try:
            if upload is None:
                raise ValidationError("請選擇學生名單檔案。")
            rows, errors = parse_students(upload)
        except (ValidationError, ValueError, UnicodeError, OSError) as error:
            context["errors"] = error.messages if isinstance(error, ValidationError) else ["檔案無法讀取，請確認格式與內容。"]
            return render(request, "courses/student_import.html", context, status=400)
        context["preview"] = rows
        context["errors"] = errors
        if not errors:
            token = secrets.token_urlsafe(24)
            request.session["student_import_preview"] = {"rows": rows, "token": token, "created": time.time()}
            context["token"] = token
    return render(request, "courses/student_import.html", context, status=400 if context.get("errors") else 200)


@school_required
@require_POST
def student_import_confirm(request):
    preview = request.session.get("student_import_preview")
    if not preview or not secrets.compare_digest(str(request.POST.get("token", "")), preview["token"]) or time.time() - preview["created"] > 900:
        messages.error(request, "學生名單預覽已失效，請重新上傳。")
        return redirect("school:student_import")
    request.session.pop("student_import_preview", None)
    try:
        with transaction.atomic():
            for row in preview["rows"]:
                existing = User.objects.filter(pk=row["existing_id"]).first() if row["existing_id"] else None
                if row["existing_id"] and (not existing or existing.role != User.Role.STUDENT):
                    raise ValidationError("學生帳號狀態已改變，請重新上傳名單。")
                if User.objects.filter(email__iexact=row["email"]).exclude(pk=existing.pk if existing else None).exists():
                    raise ValidationError("Email 已被使用，請重新上傳名單。")
                if existing:
                    existing.email = row["email"]
                    existing.email_verified_at = None
                    if row["display_name"]:
                        existing.display_name = row["display_name"]
                    if row["student_class_id"]:
                        existing.student_class_id = row["student_class_id"]
                    existing.save()
                else:
                    if User.objects.filter(username__iexact=row["username"]).exists():
                        raise ValidationError("學號已被使用，請重新上傳名單。")
                    User.objects.create(
                        username=row["username"], email=row["email"],
                        password=row["password_hash"], display_name=row["display_name"],
                        student_class_id=row["student_class_id"], role=User.Role.STUDENT,
                    )
    except (ValidationError, IntegrityError) as error:
        messages.error(request, error.messages[0] if isinstance(error, ValidationError) else "名單資料已變更，請重新上傳。")
        return redirect("school:student_import")
    created = sum(row["action"] == "建立" for row in preview["rows"])
    messages.success(request, f"學生匯入完成：新增 {created} 位、更新 {len(preview['rows']) - created} 位。")
    return redirect("school:student_import")


@school_required
def student_import_template(request):
    from openpyxl import Workbook
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "學生名單"
    sheet.append(["學號", "Email", "姓名", "系所代碼", "班級代碼", "初始密碼"])
    sheet.freeze_panes = "A2"
    for column in "ABCDEF":
        sheet.column_dimensions[column].width = 24
    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()
    response = HttpResponse(buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="student-import-template.xlsx"'
    return response
