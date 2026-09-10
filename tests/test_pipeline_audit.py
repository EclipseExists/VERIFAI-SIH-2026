"""VERIFAI Pipeline Audit & Regression Test Suite
================================================
Covers:
1. Genuine synthetic passport MRZ & OCR extraction
2. Corrupted test fixtures checksum validation
3. Real test document MRZ checksum math
4. Visual Inspection Zone (VIZ) vs MRZ cross-field consistency
5. Forensics ELA and noise inconsistency calibration
6. Risk scoring and signal generation
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest

# Ensure paths are set
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ai.ocr_mrz.checksum import validate_td3_checksums
from ai.ocr_mrz.mrz_parser import parse_td3_mrz
from ai.mrz.parse import parse_mrz
try:
    from app.api.risk import _collect_signals, _compute_final_score
except ImportError:
    from backend.app.api.risk import _collect_signals, _compute_final_score  # type: ignore


def test_td3_mathematical_checksum_whatsapp_document():
    """Verify ICAO 9303 checksum calculation on the real WhatsApp passport MRZ."""
    line1 = "P<TAPIA<JUAN<DASEC<<<<<<<<<<<<<<<<<<<<<<<<<<"
    line2 = "KV24247253ESP7809062M3202193A3064941000<<<30"

    val = validate_td3_checksums(line2)
    assert val.passport_number is True, "Passport number check digit should be valid"
    assert val.date_of_birth is True, "DOB check digit should be valid"
    assert val.expiry_date is True, "Expiry check digit should be valid"
    assert val.personal_number is True, "Personal number check digit should be valid"
    assert val.final is True, "Composite check digit should be valid"
    assert val.overall is True, "Overall checksum should be 100% valid"

    identity = parse_td3_mrz(line1, line2)
    assert identity.passport_number == "KV2424725"
    assert identity.date_of_birth == "1978-09-06"
    assert identity.expiry_date == "2032-02-19"
    assert identity.nationality == "ESP"
    assert identity.surname == "TAPIA"
    assert identity.given_names == "JUAN DASEC"


def test_corrupted_fixtures_checksum_validation():
    """Verify that every corrupted fixture fails its respective check digit."""
    corrupted_cases = [
        ("passport_corrupted_checksum_digit.png", "composite"),
        ("passport_corrupted_dob.png", "date_of_birth"),
        ("passport_corrupted_expiry_date.png", "expiry_date"),
        ("passport_corrupted_passport_number.png", "passport_number"),
    ]

    for fname, expected_failing_field in corrupted_cases:
        path = ROOT_DIR / "data" / "passports" / fname
        if not path.exists():
            continue
        res = parse_mrz(str(path))
        assert res["mrz_present"] is True
        assert res["checksum_valid"] is False, f"{fname} should fail checksum validation"
        details_map = {d["field"]: d["valid"] for d in res["checksum_details"]}
        assert details_map.get(expected_failing_field) is False, (
            f"{fname} expected {expected_failing_field} to be False, got {details_map}"
        )


def test_cross_field_consistency_dob_mismatch():
    """Verify that a discrepancy between Visual Inspection Zone (VIZ) DOB and MRZ DOB is flagged."""
    mrz_obj = SimpleNamespace(
        mrz_present=True,
        checksum_valid=True,
        parsed_fields={
            "passport_number": "KV2424725",
            "date_of_birth": "1978-09-06",
            "expiry_date": "2032-02-19",
        },
        is_stub=False,
    )
    ocr_obj = SimpleNamespace(
        structured_fields={
            "doc_number": "KV2424725",
            "dob": "1988-08-08",  # 10-year discrepancy from MRZ!
            "expiry": "2032-02-19",
        },
        field_confidence={"dob": 0.99, "expiry": 0.99, "doc_number": 0.99},
        document_id="00000000-0000-0000-0000-000000000001",
        is_stub=False,
    )
    forensics_obj = SimpleNamespace(
        overall_manipulation_probability=0.218,
        is_stub=False,
    )
    face_obj = SimpleNamespace(
        band="match",
        similarity_score=0.982,
    )

    signals = _collect_signals(
        case_id="audit-test",
        ocr_result=ocr_obj,
        mrz_result=mrz_obj,
        forensics_result=forensics_obj,
        face_result=face_obj,
    )

    sig_names = [s["signal_name"] for s in signals]
    assert "dob_mismatch" in sig_names, "dob_mismatch signal must be triggered"
    assert "mrz_visual_mismatch" in sig_names, "mrz_visual_mismatch signal must be triggered"
    assert "quality_check_passed" not in sig_names, "quality_check_passed must NOT be awarded when cross-check fails"

    score, band = _compute_final_score(signals)
    assert score >= 30.0, f"Score should be at least 30.0 (Medium Risk) due to DOB mismatch, got {score}"
    assert band in ("medium", "high"), f"Band should be medium or high, got {band}"


def test_forensics_metrics_calibration():
    """Verify that forensics produces calibrated float values and does not false-flag genuine images."""
    path = ROOT_DIR / "data" / "passports" / "passport_genuine.png"
    if path.exists():
        res = analyze_document(str(path))
        assert isinstance(res["ela_score"], float)
        assert isinstance(res["noise_inconsistency_score"], float)
        assert isinstance(res["overall_manipulation_probability"], float)
        assert res["overall_manipulation_probability"] < 0.35, "Genuine image should have low manipulation probability"


def test_clean_document_scoring():
    """Verify that a genuine document with matching face gets low risk score."""
    mrz_obj = SimpleNamespace(
        mrz_present=True,
        checksum_valid=True,
        parsed_fields={
            "passport_number": "L898902C3",
            "date_of_birth": "1974-08-12",
            "expiry_date": "2032-10-23",
        },
        is_stub=False,
    )
    ocr_obj = SimpleNamespace(
        structured_fields={
            "name": "ERIKSSON ANNA",
            "doc_number": "L898902C3",
            "dob": "1974-08-12",
            "expiry": "2032-10-23",
        },
        field_confidence={"dob": 0.99, "expiry": 0.99, "doc_number": 0.99, "name": 0.99},
        document_id="00000000-0000-0000-0000-000000000001",
        is_stub=False,
    )
    forensics_obj = SimpleNamespace(
        overall_manipulation_probability=0.071,
        is_stub=False,
    )
    face_obj = SimpleNamespace(
        band="match",
        similarity_score=0.98,
    )

    signals = _collect_signals(
        case_id="clean-test",
        ocr_result=ocr_obj,
        mrz_result=mrz_obj,
        forensics_result=forensics_obj,
        face_result=face_obj,
    )
    score, band = _compute_final_score(signals)
    assert score == 0.0, f"Clean document score should be 0.0, got {score}"
    assert band == "low", f"Clean document band should be low, got {band}"
