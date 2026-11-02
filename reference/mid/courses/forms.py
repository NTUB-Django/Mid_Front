from django import forms

from .models import Department, EduType


class OfferingFilterForm(forms.Form):
    q = forms.CharField(label="關鍵字", required=False, max_length=80)
    grade = forms.TypedChoiceField(
        label="年級", required=False, coerce=int, empty_value=None,
        choices=[("", "全部年級")] + [(n, f"{n} 年級") for n in range(1, 6)],
    )
    edu = forms.ModelChoiceField(
        label="學制",
        required=False,
        queryset=EduType.objects.all(),
        empty_label="全部學制",
    )
    dept = forms.ModelChoiceField(
        label="系所",
        required=False,
        queryset=Department.objects.all(),
        empty_label="全部系所",
    )
