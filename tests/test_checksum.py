"""Unit tests for ICAO Doc 9303 Checksum Validation."""

import pytest
from ai.ocr_mrz.checksum import (
    calculate_check_digit,
    validate_check_digit,
    validate_td3_checksums,
    char_to_value,
    ICAO_WEIGHTS
)
from data.synthetic_generator import build_td3_mrz, corrupt_mrz


def test_char_to_value():
    """Verify ICAO character numeric mapping."""
    # Digits
    for i in range(10):
        assert char_to_value(str(i)) == i
    # Letters: A=10, Z=35
    assert char_to_value('A') == 10
    assert char_to_value('B') == 11
    assert char_to_value('L') == 21
    assert char_to_value('Z') == 35
    # Filler
    assert char_to_value('<') == 0

    # Invalid characters raise ValueError
    with pytest.raises(ValueError):
        char_to_value('$')


def test_calculate_check_digit_known_values():
    """Verify check digit calculation against known ICAO Doc 9303 examples."""
    # Document number: L898902C3 -> 6
    assert calculate_check_digit("L898902C3") == "6"

    # Date of birth: 740812 -> 2
    # 7*7 + 4*3 + 0*1 + 8*7 + 1*3 + 2*1 = 49 + 12 + 0 + 56 + 3 + 2 = 122 -> 2
    assert calculate_check_digit("740812") == "2"

    # Expiry: 120415 -> 9
    # 1*7 + 2*3 + 0*1 + 4*7 + 1*3 + 5*1 = 7 + 6 + 0 + 28 + 3 + 5 = 49 -> 9
    assert calculate_check_digit("120415") == "9"


def test_valid_passport_mrz(genuine_td3_mrz):
    """Verify that a genuine synthetic TD3 MRZ passes all checksums."""
    line1, line2 = genuine_td3_mrz
    result = validate_td3_checksums(line2)

    assert result.passport_number is True
    assert result.date_of_birth is True
    assert result.expiry_date is True
    assert result.final is True
    assert result.overall is True


def test_invalid_passport_checksum(genuine_td3_mrz):
    """Verify that altering the passport number invalidates passport and composite checks."""
    line1, line2 = genuine_td3_mrz
    c_l1, c_l2, desc = corrupt_mrz(line1, line2, "passport_number")

    result = validate_td3_checksums(c_l2)
    assert result.passport_number is False
    assert result.date_of_birth is True
    assert result.expiry_date is True
    assert result.final is False  # Composite includes passport number!
    assert result.overall is False


def test_invalid_dob_checksum(genuine_td3_mrz):
    """Verify that altering the DOB invalidates DOB and composite checks."""
    line1, line2 = genuine_td3_mrz
    c_l1, c_l2, desc = corrupt_mrz(line1, line2, "dob")

    result = validate_td3_checksums(c_l2)
    assert result.passport_number is True
    assert result.date_of_birth is False
    assert result.expiry_date is True
    assert result.final is False  # Composite includes DOB!
    assert result.overall is False


def test_invalid_expiry_checksum(genuine_td3_mrz):
    """Verify that altering the expiry date invalidates expiry and composite checks."""
    line1, line2 = genuine_td3_mrz
    c_l1, c_l2, desc = corrupt_mrz(line1, line2, "expiry_date")

    result = validate_td3_checksums(c_l2)
    assert result.passport_number is True
    assert result.date_of_birth is True
    assert result.expiry_date is False
    assert result.final is False
    assert result.overall is False


def test_corrupted_composite_check_digit(genuine_td3_mrz):
    """Verify that directly modifying the final check digit fails composite validation."""
    line1, line2 = genuine_td3_mrz
    # Flip the 44th character (index 43)
    l2 = list(line2)
    l2[43] = '0' if l2[43] != '0' else '9'
    tampered_l2 = "".join(l2)

    result = validate_td3_checksums(tampered_l2)
    assert result.passport_number is True
    assert result.date_of_birth is True
    assert result.expiry_date is True
    assert result.final is False
    assert result.overall is False


def test_malformed_mrz_length():
    """Verify that irregular line length immediately fails validation."""
    short_line2 = "L898902C36UTO7408122F3210239ZE123456789012"  # 42 chars instead of 44
    result = validate_td3_checksums(short_line2)
    assert result.overall is False
    assert result.passport_number is False
