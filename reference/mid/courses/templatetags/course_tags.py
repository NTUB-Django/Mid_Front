from django import template

register = template.Library()

STATUS_LABELS = {
    "pre": "預選中",
    "selected": "已在課表",
    "rejected": "未選上",
}

WEEKDAY_NAMES = {
    1: "星期一",
    2: "星期二",
    3: "星期三",
    4: "星期四",
    5: "星期五",
    6: "星期六",
    7: "星期日",
}


@register.filter
def get_item(mapping, key):
    if mapping is None:
        return None
    return mapping.get(key)


@register.filter
def status_label(status):
    return STATUS_LABELS.get(status, status or "—")


@register.filter
def weekday_name(day_num):
    return WEEKDAY_NAMES.get(day_num, f"星期{day_num}")
