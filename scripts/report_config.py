from copy import deepcopy
from datetime import date, datetime

from config.settings import load_report_settings


def ordinal_day(day):
    if 10 <= day % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix}"


def format_report_date(value):
    if not value or value.lower() == "today":
        parsed = date.today()
    else:
        parsed = None
        for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%B %d, %Y", "%b %d, %Y"):
            try:
                parsed = datetime.strptime(value, pattern).date()
                break
            except ValueError:
                continue
        if parsed is None:
            return value.strip()
    return f"{ordinal_day(parsed.day)} {parsed.strftime('%B %Y')}"


def build_report_settings(report_date=None, recipient_overrides=None):
    settings = deepcopy(load_report_settings())
    settings["report_date"] = format_report_date(report_date or settings.get("report_date", "today"))
    for key, value in (recipient_overrides or {}).items():
        if value is not None:
            settings["recipient"][key] = value
    return settings
