"""Synthetic Demo Data Generator for VERIFAI.

Generates valid synthetic TD3 passport MRZ data (with mathematically sound ICAO checksums)
and creates deliberately corrupted/tampered variants for demonstration and testing.
Strictly uses fictional/synthetic data. No real personal information is used.
"""

import os
import sys
from pathlib import Path
from typing import Tuple, Dict, Any, List

# Ensure verifai root is in Python path
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.ocr_mrz.checksum import calculate_check_digit, validate_td3_checksums, get_td3_composite_data
from ai.ocr_mrz.utils import create_synthetic_passport_image
import cv2


def build_td3_mrz(
    issuing_country: str = "UTO",
    surname: str = "SPECIMEN",
    given_names: str = "JANE DOE",
    passport_number: str = "A12345678",
    nationality: str = "UTO",
    dob_yymmdd: str = "900101",
    sex: str = "F",
    expiry_yymmdd: str = "300101",
    personal_number: str = "12345678901234"
) -> Tuple[str, str]:
    """Build a mathematically valid TD3 MRZ (2 lines of 44 characters)."""
    # 1. Format Line 1
    doc_prefix = "P<"
    country_code = (issuing_country + "<<<")[:3]

    clean_surname = surname.upper().replace(" ", "<")
    clean_given = given_names.upper().replace(" ", "<")
    name_field = f"{clean_surname}<<{clean_given}"
    name_44 = (name_field + "<" * 39)[:39]

    line1 = f"{doc_prefix}{country_code}{name_44}"
    if len(line1) != 44:
        raise ValueError(f"Line 1 length is {len(line1)}, expected 44")

    # 2. Format Line 2
    clean_pnum = (passport_number.upper() + "<" * 9)[:9]
    pnum_check = calculate_check_digit(clean_pnum)

    nat_code = (nationality.upper() + "<<<")[:3]

    dob_check = calculate_check_digit(dob_yymmdd)

    clean_sex = sex.upper() if sex.upper() in ('M', 'F') else '<'

    exp_check = calculate_check_digit(expiry_yymmdd)

    clean_opt = (personal_number.upper() + "<" * 14)[:14]
    opt_check = calculate_check_digit(clean_opt)

    # Partial line 2 for composite check:
    # composite data = line2[0:10] + line2[13:20] + line2[21:43]
    composite_data = (
        clean_pnum + pnum_check +
        dob_yymmdd + dob_check +
        expiry_yymmdd + exp_check + clean_opt + opt_check
    )
    final_check = calculate_check_digit(composite_data)

    line2 = (
        clean_pnum + pnum_check +
        nat_code +
        dob_yymmdd + dob_check +
        clean_sex +
        expiry_yymmdd + exp_check +
        clean_opt + opt_check +
        final_check
    )

    if len(line2) != 44:
        raise ValueError(f"Line 2 length is {len(line2)}, expected 44")

    return line1, line2


def corrupt_mrz(line1: str, line2: str, corruption_type: str) -> Tuple[str, str, str]:
    """Deliberately corrupt an MRZ to test tampering detection.

    Returns:
        Tuple of (corrupted_line1, corrupted_line2, description)
    """
    l1 = list(line1)
    l2 = list(line2)

    if corruption_type == "passport_number":
        # Modify a character in passport number without recalculating check digit
        orig_char = l2[3]
        new_char = '9' if orig_char != '9' else '1'
        l2[3] = new_char
        desc = f"Altered passport number char at index 3: '{orig_char}' -> '{new_char}'"

    elif corruption_type == "dob":
        # Modify birth year from 90 to 80
        orig = "".join(l2[13:15])
        l2[13] = '8'
        l2[14] = '0'
        desc = f"Altered DOB year: '{orig}' -> '80'"

    elif corruption_type == "expiry_date":
        # Modify expiry year
        orig = "".join(l2[21:23])
        l2[21] = '3'
        l2[22] = '5'
        desc = f"Altered Expiry year: '{orig}' -> '35'"

    elif corruption_type == "checksum_digit":
        # Invert the passport check digit
        orig_check = l2[9]
        new_check = '0' if orig_check != '0' else '7'
        l2[9] = new_check
        desc = f"Directly forged check digit at index 9: '{orig_check}' -> '{new_check}'"

    elif corruption_type == "name":
        # Change surname in Line 1
        l1[5] = 'Z'
        l1[6] = 'Z'
        desc = "Altered name field in Line 1"

    elif corruption_type == "ocr_confusion":
        # Simulate OCR confusion: '0' -> 'O' in passport number
        for i in range(9):
            if l2[i] == '0':
                l2[i] = 'O'
                break
        else:
            l2[0] = 'O'
        desc = "Simulated OCR character confusion ('0' -> 'O')"

    else:
        raise ValueError(f"Unknown corruption type: {corruption_type}")

    return "".join(l1), "".join(l2), desc


def generate_synthetic_dataset(output_dir: str):
    """Generate sample genuine and corrupted passport documents and images."""
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 70)
    print("VERIFAI SYNTHETIC DEMO DATA GENERATOR")
    print("=" * 70)

    # 1. Genuine Passport
    line1, line2 = build_td3_mrz(
        issuing_country="UTO",
        surname="ERIKSSON",
        given_names="ANNA MARIA",
        passport_number="L898902C3",
        nationality="UTO",
        dob_yymmdd="740812",
        sex="F",
        expiry_yymmdd="321023",
        personal_number="ZE123456789012"
    )

    val_res = validate_td3_checksums(line2)
    print("\n[GENUINE PASSPORT]")
    print(f"Line 1: {line1}")
    print(f"Line 2: {line2}")
    print(f"Validation: overall={val_res.overall}, passport={val_res.passport_number}, "
          f"dob={val_res.date_of_birth}, expiry={val_res.expiry_date}, final={val_res.final}")
    assert val_res.overall is True, "Genuine MRZ must pass all checksums!"

    genuine_img = create_synthetic_passport_image(line1, line2, country="UTOPIA", title="PASSPORT")
    genuine_path = os.path.join(output_dir, "passport_genuine.png")
    cv2.imwrite(genuine_path, genuine_img)
    print(f"Saved genuine image -> {genuine_path}")

    # 2. Corrupted Passports
    corruption_types = ["passport_number", "dob", "expiry_date", "checksum_digit", "ocr_confusion"]
    for c_type in corruption_types:
        c_l1, c_l2, desc = corrupt_mrz(line1, line2, c_type)
        c_val = validate_td3_checksums(c_l2)
        print(f"\n[CORRUPTED VARIANT: {c_type.upper()}]")
        print(f"Description: {desc}")
        print(f"Line 1: {c_l1}")
        print(f"Line 2: {c_l2}")
        print(f"Validation: overall={c_val.overall}, passport={c_val.passport_number}, "
              f"dob={c_val.date_of_birth}, expiry={c_val.expiry_date}, final={c_val.final}")

        c_img = create_synthetic_passport_image(c_l1, c_l2, country="UTOPIA", title="PASSPORT [ALTERED]")
        c_path = os.path.join(output_dir, f"passport_corrupted_{c_type}.png")
        cv2.imwrite(c_path, c_img)
        print(f"Saved corrupted image -> {c_path}")

    print("\n" + "=" * 70)
    print(f"Dataset successfully created at: {output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    out = os.path.join(PROJECT_ROOT, "data", "passports")
    generate_synthetic_dataset(out)
