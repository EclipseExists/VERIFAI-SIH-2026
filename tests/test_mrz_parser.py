"""Unit tests for TD3 MRZ Parser and Date Normalization."""

import pytest
from ai.ocr_mrz.mrz_parser import parse_td3_mrz, parse_mrz_date
from data.synthetic_generator import build_td3_mrz


def test_parse_valid_td3_mrz():
    """Verify correct field extraction from a standard TD3 MRZ."""
    line1, line2 = build_td3_mrz(
        issuing_country="GBR",
        surname="SMITH",
        given_names="JOHN EDWARD",
        passport_number="987654321",
        nationality="GBR",
        dob_yymmdd="850615",
        sex="M",
        expiry_yymmdd="350615",
        personal_number="ID123456789012"
    )

    identity = parse_td3_mrz(line1, line2)

    assert identity.document_type == "P"
    assert identity.issuing_state == "GBR"
    assert identity.surname == "SMITH"
    assert identity.given_names == "JOHN EDWARD"
    assert identity.name == "SMITH JOHN EDWARD"
    assert identity.passport_number == "987654321"
    assert identity.nationality == "GBR"
    assert identity.sex == "M"
    assert identity.date_of_birth == "1985-06-15"
    assert identity.raw_date_of_birth == "850615"
    assert identity.expiry_date == "2035-06-15"
    assert identity.raw_expiry_date == "350615"
    assert identity.personal_number == "ID123456789012"


def test_single_surname_mononym():
    """Verify parsing when holder has only a single name without given names."""
    # 5 + 9 + 30 = 44 characters
    line1 = "P<INDRAMANUJAN" + "<" * 30
    line2 = "Z123456784IND8712228M2712224<<<<<<<<<<<<<<02"

    identity = parse_td3_mrz(line1, line2)
    assert identity.surname == "RAMANUJAN"
    assert identity.given_names == ""
    assert identity.name == "RAMANUJAN"


def test_parse_mrz_date_valid():
    """Verify ISO conversion for valid DOB and expiry dates."""
    # DOB for 1974-08-12
    assert parse_mrz_date("740812", is_expiry=False) == "1974-08-12"
    # DOB for 2005-03-20
    assert parse_mrz_date("050320", is_expiry=False) == "2005-03-20"
    # Expiry for 2032-10-23
    assert parse_mrz_date("321023", is_expiry=True) == "2032-10-23"


def test_parse_mrz_date_invalid():
    """Verify that malformed dates return None."""
    assert parse_mrz_date("741312", is_expiry=False) is None  # Month 13
    assert parse_mrz_date("740832", is_expiry=False) is None  # Day 32
    assert parse_mrz_date("ABCDEF", is_expiry=False) is None  # Non-numeric
    assert parse_mrz_date("12345", is_expiry=False) is None   # Length != 6


def test_parse_invalid_length_raises():
    """Verify ValueError is raised if lines are not 44 characters."""
    with pytest.raises(ValueError, match="Expected 44 characters each"):
        parse_td3_mrz("P<UTOERIKSSON<<<<<<<<<<<<<<<<<<<<<<<<<<<", "L898902C36UTO")
