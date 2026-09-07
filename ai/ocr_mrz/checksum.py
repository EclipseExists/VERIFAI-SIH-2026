"""ICAO Doc 9303 MRZ Checksum Implementation.

Implements the standard 7-3-1 weighted modulus 10 check digit algorithm
for Machine Readable Travel Documents (MRTD) conforming to ICAO 9303.
"""

from typing import Tuple, Dict, Any, Optional
from ai.ocr_mrz.models import MRZValidationResult

# Standard ICAO 7-3-1 weight cycle
ICAO_WEIGHTS = (7, 3, 1)


def char_to_value(char: str) -> int:
    """Convert an MRZ character to its numeric value according to ICAO 9303.

    - '0'-'9': 0-9
    - 'A'-'Z': 10-35
    - '<': 0
    Any other character raises ValueError.
    """
    c = char.upper()
    if '0' <= c <= '9':
        return ord(c) - ord('0')
    if 'A' <= c <= 'Z':
        return ord(c) - ord('A') + 10
    if c == '<':
        return 0
    raise ValueError(f"Invalid MRZ character for checksum: {char!r}")


def calculate_check_digit(data: str) -> str:
    """Calculate the ICAO 9303 check digit for a string.

    Args:
        data: Alphanumeric string containing only 0-9, A-Z, or <.

    Returns:
        Single character check digit ('0'-'9').
    """
    total = 0
    for idx, char in enumerate(data):
        weight = ICAO_WEIGHTS[idx % 3]
        total += char_to_value(char) * weight
    return str(total % 10)


def validate_check_digit(data: str, expected_digit: str) -> bool:
    """Verify whether a data field matches its expected check digit.

    Args:
        data: The payload string.
        expected_digit: The check digit character (or '<' in certain optional fields).

    Returns:
        True if valid, False otherwise.
    """
    if not expected_digit:
        return False

    # In optional fields, if all data is '<' and check digit is '<', it is valid
    if expected_digit == '<' and set(data) <= {'<'}:
        return True

    # If expected digit is '<', check if calculated value is 0
    try:
        calculated = calculate_check_digit(data)
        if expected_digit == calculated:
            return True
        if expected_digit == '<' and calculated == '0':
            return True
        return False
    except ValueError:
        return False


def get_td3_composite_data(line2: str) -> str:
    """Extract the 39-character composite string from a 44-character TD3 line 2.

    According to ICAO Doc 9303 Part 4:
    Positions validated:
    - 0..10: Passport number + check digit (chars 1-10)
    - 13..20: Date of birth + check digit (chars 14-20)
    - 21..43: Expiry date + check digit + optional data + optional check digit (chars 22-43)
    (Nationality at 10..13 and Sex at 20 are excluded).
    """
    if len(line2) < 44:
        raise ValueError(f"TD3 line 2 must be 44 characters, got {len(line2)}")
    return line2[0:10] + line2[13:20] + line2[21:43]


def validate_td3_checksums(line2: str) -> MRZValidationResult:
    """Validate all individual and composite checksums on TD3 Line 2.

    Line 2 format (44 characters):
    0-8:   Passport number (9)
    9:     Passport number check digit (1)
    10-12: Nationality (3)
    13-18: Date of birth (6)
    19:    Date of birth check digit (1)
    20:    Sex (1)
    21-26: Expiry date (6)
    27:    Expiry date check digit (1)
    28-41: Optional data (14)
    42:    Optional data check digit (1)
    43:    Composite check digit (1)
    """
    if len(line2) != 44:
        return MRZValidationResult(
            passport_number=False,
            date_of_birth=False,
            expiry_date=False,
            personal_number=False,
            final=False,
            overall=False
        )

    # 1. Passport number check digit
    doc_num_data = line2[0:9]
    doc_num_check = line2[9]
    valid_doc_num = validate_check_digit(doc_num_data, doc_num_check)

    # 2. Date of birth check digit
    dob_data = line2[13:19]
    dob_check = line2[19]
    valid_dob = validate_check_digit(dob_data, dob_check)

    # 3. Expiry date check digit
    exp_data = line2[21:27]
    exp_check = line2[27]
    valid_exp = validate_check_digit(exp_data, exp_check)

    # 4. Optional / personal number check digit (optional)
    opt_data = line2[28:42]
    opt_check = line2[42]
    # If optional field is completely unused ('<<<<<<<<<<<<<<' and '<'), treated as valid
    if set(opt_data) <= {'<'} and opt_check == '<':
        valid_opt = True
    else:
        valid_opt = validate_check_digit(opt_data, opt_check)

    # 5. Composite check digit
    composite_data = get_td3_composite_data(line2)
    final_check = line2[43]
    valid_final = validate_check_digit(composite_data, final_check)

    # Overall is true iff all core check digits are valid
    overall = valid_doc_num and valid_dob and valid_exp and valid_final and (valid_opt if opt_check != '<' or set(opt_data) <= {'<'} else True)

    return MRZValidationResult(
        passport_number=valid_doc_num,
        date_of_birth=valid_dob,
        expiry_date=valid_exp,
        personal_number=valid_opt,
        final=valid_final,
        overall=overall
    )
