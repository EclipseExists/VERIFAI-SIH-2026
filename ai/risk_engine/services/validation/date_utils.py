"""Date Parsing Utilities for Document Validation.

Adapted from teammate's code. Self-contained.
"""

from datetime import date, datetime
import re
from typing import Optional, Tuple, Union

DATE_FORMATS = [
    "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %m %Y",
    "%Y/%m/%d", "%Y.%m.%d", "%d %b %Y", "%d-%b-%Y", "%d %B %Y",
    "%b %d, %Y", "%B %d, %Y", "%d/%m/%y", "%d-%m-%y", "%Y%m%d",
]


def clean_date_string(val: str) -> str:
    if not val:
        return ""
    cleaned = val.strip().strip("'\".,;:-_")
    return re.sub(r"\s+", " ", cleaned)


def parse_mrz_6digit_date(cleaned: str, is_dob: bool = False) -> Optional[date]:
    if not (len(cleaned) == 6 and cleaned.isdigit()):
        return None
    yy, mm, dd = int(cleaned[0:2]), int(cleaned[2:4]), int(cleaned[4:6])
    if mm < 1 or mm > 12 or dd < 1 or dd > 31:
        return None
    current_yy = date.today().year % 100
    if is_dob:
        year = 2000 + yy if yy <= current_yy else 1900 + yy
    else:
        year = 2000 + yy if yy < 50 else 1900 + yy
    try:
        return date(year, mm, dd)
    except ValueError:
        return None


def parse_date(val: Union[str, date, datetime, None], is_dob: bool = False) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if not isinstance(val, str):
        val = str(val)
    cleaned = clean_date_string(val)
    if not cleaned:
        return None
    try:
        return date.fromisoformat(cleaned)
    except (ValueError, TypeError):
        pass
    if len(cleaned) == 6 and cleaned.isdigit():
        mrz_date = parse_mrz_6digit_date(cleaned, is_dob=is_dob)
        if mrz_date:
            return mrz_date
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def parse_date_with_status(
    val: Union[str, date, datetime, None],
    field_name: str = "date",
    is_dob: bool = False,
) -> Tuple[Optional[date], bool, str]:
    if val is None or (isinstance(val, str) and not val.strip()):
        return None, True, f"{field_name.capitalize()} is not provided."
    parsed = parse_date(val, is_dob=is_dob)
    if parsed is not None:
        return parsed, True, f"Successfully parsed {field_name}: {parsed.isoformat()}"
    cleaned = clean_date_string(str(val))
    return None, False, f"{field_name.capitalize()} '{cleaned}' is malformed or cannot be parsed."
