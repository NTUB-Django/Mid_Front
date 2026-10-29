from datetime import time
from django import forms

from courses.models import Department, EduType, OfferingSlot, StudentClass

from .models import COLOR_CHOICES, CustomSchedule, Selection
from accounts.social import member_groups


STANDARD_PERIOD_TIMES = [
    ("第一節", time(8, 10), time(9, 0)),
    ("第二節", time(9, 10), time(10, 0)),
    ("第三節", time(10, 10), time(11, 0)),
    ("第四節", time(11, 10), time(12, 0)),
    ("第五節", time(13, 30), time(14, 20)),
    ("第六節", time(14, 25), time(15, 15)),
    ("第七節", time(15, 25), time(16, 15)),
    ("第八節", time(16, 20), time(17, 10)),
    ("第九節", time(17, 15), time(18, 5)),
    ("第十節", time(18, 30), time(19, 15)),
    ("第十一節", time(19, 20), time(20, 5)),
    ("第十二節", time(20, 15), time(21, 0)),
    ("第十三節", time(21, 5), time(21, 50)),
]


class CustomScheduleForm(forms.ModelForm):
    visibility = forms.ChoiceField(label="行程可見範圍", choices=CustomSchedule.Visibility.choices, required=False, widget=forms.Select(attrs={"class": "input"}))
    start = forms.TimeField(
        label="開始時間",
        widget=forms.TimeInput(attrs={"type": "time", "class": "input"}),
    )
    end = forms.TimeField(
        label="結束時間",
        widget=forms.TimeInput(attrs={"type": "time", "class": "input"}),
    )

    class Meta:
        model = CustomSchedule
        fields = ["title", "weekday", "period", "start", "end", "location", "color", "note", "visibility", "shared_groups"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "input", "placeholder": "例如：系學會開會、兼職打工、自習"}),
            "weekday": forms.Select(attrs={"class": "input"}),
            "period": forms.TextInput(attrs={"class": "input", "placeholder": "例如：第五節、晚上、彈性時段"}),
            "location": forms.TextInput(attrs={"class": "input", "placeholder": "例如：圖書館 2F、外社辦、六館 302"}),
            "color": forms.Select(attrs={"class": "input"}),
            "note": forms.Textarea(attrs={"class": "input", "rows": 3, "placeholder": "備註事項或說明..."}),
            "shared_groups": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["shared_groups"].queryset = member_groups(user) if user else self.fields["shared_groups"].queryset.none()

    def clean_visibility(self):
        return self.cleaned_data.get("visibility") or CustomSchedule.Visibility.INHERIT

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start")
        end = cleaned_data.get("end")
        if start and end and start >= end:
            raise forms.ValidationError("結束時間必須晚於開始時間！")
        if cleaned_data.get("visibility") == CustomSchedule.Visibility.GROUPS and not cleaned_data.get("shared_groups"):
            self.add_error("shared_groups", "請選擇至少一個已加入的群組。")
        return cleaned_data


class ImportClassScheduleForm(forms.Form):
    edu = forms.ModelChoiceField(
        label="學制",
        queryset=EduType.objects.all(),
        required=False,
        empty_label="-- 請選擇學制 --",
        widget=forms.Select(attrs={"class": "input", "id": "id_import_edu"}),
    )
    dept = forms.ModelChoiceField(
        label="系所",
        queryset=Department.objects.all(),
        required=False,
        empty_label="-- 請選擇系所 --",
        widget=forms.Select(attrs={"class": "input", "id": "id_import_dept"}),
    )
    student_class = forms.ModelChoiceField(
        label="班級",
        queryset=StudentClass.objects.select_related("dept", "dept__edu").all(),
        required=True,
        empty_label="-- 請選擇要匯入的班級 --",
        widget=forms.Select(attrs={"class": "input", "id": "id_import_class"}),
    )


class SelectionPreferenceForm(forms.ModelForm):
    class Meta:
        model = Selection
        fields = ["notes", "color"]
        widgets = {
            "notes": forms.TextInput(attrs={"class": "input", "placeholder": "自訂這門課的備註或代辦事項"}),
            "color": forms.Select(attrs={"class": "input"}),
        }
