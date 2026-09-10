"""TD3 Passport MRZ Parser and Date Normalizer.

Parses standard 2-line x 44-character Machine Readable Travel Document (TD3)
zones and converts dates to ISO 8601 (YYYY-MM-DD) format.
"""

from datetime import datetime
from typing import Optional, Tuple
from ai.ocr_mrz.models import IdentityData


def parse_mrz_date(raw_date: str, is_expiry: bool = False) -> Optional[str]:
    """Convert a 6-digit MRZ date (YYMMDD) into an ISO 8601 (YYYY-MM-DD) date string.

    Args:
        raw_date: 6-character string (YYMMDD).
        is_expiry: If True, uses expiry date pivot rules; otherwise uses DOB pivot rules.

    Returns:
        ISO formatted date string 'YYYY-MM-DD' or None if invalid.
    """
    if len(raw_date) != 6 or not raw_date.isdigit():
        return None

    yy = int(raw_date[0:2])
    mm = int(raw_date[2:4])
    dd = int(raw_date[4:6])

    # Validate month and day bounds
    if not (1 <= mm <= 12 and 1 <= dd <= 31):
        return None

    current_year = datetime.now().year
    current_yy = current_year % 100

    if is_expiry:
        # Passports are typically valid up to 10-15 years into the future.
        # If yy <= current_yy + 30, it is in 2000s; otherwise 1900s.
        year = 2000 + yy if yy <= (current_yy + 30) else 1900 + yy
    else:
        # Date of Birth pivot:
        # People born up to current year are in 2000s, older in 1900s.
        year = 2000 + yy if yy <= current_yy else 1900 + yy

    try:
        dt = datetime(year, mm, dd)
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        # Catches invalid dates such as Feb 30 or non-leap Feb 29
        return None


def parse_td3_mrz(line1: str, line2: str) -> IdentityData:
    """Parse a validated 2-line TD3 MRZ into structured IdentityData.

    Line 1 (44 chars):
      0-1:   Document type (e.g. 'P<')
      2-4:   Issuing state (3 chars)
      5-43:  Name (Primary identifier << Secondary identifier(s))

    Line 2 (44 chars):
      0-8:   Passport number (9 chars)
      9:     Check digit
      10-12: Nationality (3 chars)
      13-18: Date of birth (YYMMDD)
      19:    Check digit
      20:    Sex ('M', 'F', or '<')
      21-26: Expiry date (YYMMDD)
      27:    Check digit
      28-41: Optional data / personal number (14 chars)
      42:    Check digit
      43:    Composite check digit

    Raises:
        ValueError: If line lengths are not 44 characters.
    """
    if len(line1) != 44 or len(line2) != 44:
        raise ValueError(
            f"Invalid TD3 line lengths: line1={len(line1)}, line2={len(line2)}. Expected 44 characters each."
        )

    # Line 2 fields (parsed first to get nationality for context)
    raw_passport_num = line2[0:9].replace('<', '').strip()
    nationality = line2[10:13].replace('<', '').strip()

    # Document Type & Issuing State
    doc_type = line1[0:2].replace('<', '').strip() or "P"

    # Name breakdown (Line 1: 5..44 or 2..44)
    # Check if characters 2..5 match the 3-letter country code or if '<<' is in standard name zone
    line1_content = line1[5:].rstrip('<')
    if line1[2:5] == nationality or '<<' in line1_content:
        # Standard TD3: 2-character prefix + 3-char issuing state + Surname << Given Names (or mononym)
        issuing_state = line1[2:5].replace('<', '').strip()
        if '<<' in line1_content:
            name_parts = line1_content.split('<<', 1)
            surname = name_parts[0].replace('<', ' ').strip()
            given_names = name_parts[1].replace('<', ' ').strip()
        else:
            surname = line1_content.replace('<', ' ').strip()
            given_names = ""
    elif '<<' in line1[2:].rstrip('<'):
        name_parts = line1[2:].rstrip('<').split('<<', 1)
        surname = name_parts[0].replace('<', ' ').strip()
        given_names = name_parts[1].replace('<', ' ').strip()
        issuing_state = nationality or line1[2:5].replace('<', '').strip()
    else:
        # Fallback for single '<' delimiter format (e.g., P<SURNAME<GIVEN<NAME)
        tokens = [t for t in line1[2:].split('<') if t]
        if len(tokens) >= 2:
            surname = tokens[0]
            given_names = " ".join(tokens[1:])
        elif len(tokens) == 1:
            surname = tokens[0]
            given_names = ""
        else:
            surname = ""
            given_names = ""
        issuing_state = nationality or (line1[2:5].replace('<', '').strip() if len(line1) >= 5 else "")

    if surname and given_names:
        full_name = f"{surname} {given_names}"
    elif surname:
        full_name = surname
    else:
        full_name = given_names or "UNKNOWN"

    raw_dob = line2[13:19]
    iso_dob = parse_mrz_date(raw_dob, is_expiry=False)

    sex_char = line2[20].upper()
    if sex_char in ('M', 'F'):
        sex = sex_char
    elif sex_char in ('<', 'X'):
        sex = "X"
    else:
        sex = sex_char

    raw_expiry = line2[21:27]
    iso_expiry = parse_mrz_date(raw_expiry, is_expiry=True)

    raw_optional = line2[28:42].replace('<', '').strip()
    personal_number = raw_optional if raw_optional else None

    return IdentityData(
        name=full_name,
        surname=surname,
        given_names=given_names,
        passport_number=raw_passport_num,
        nationality=nationality,
        issuing_state=issuing_state,
        date_of_birth=iso_dob,
        raw_date_of_birth=raw_dob,
        sex=sex,
        expiry_date=iso_expiry,
        raw_expiry_date=raw_expiry,
        personal_number=personal_number,
        document_type=doc_type
    )
