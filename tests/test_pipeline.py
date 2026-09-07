"""Integration and End-to-End Pipeline Tests for VERIFAI."""

import pytest
import numpy as np
from ai.ocr_mrz.pipeline import VerificationPipeline
from ai.ocr_mrz.ocr_engine import MockOCREngine
from ai.ocr_mrz.models import OCRLine, BoundingBox
from ai.ocr_mrz.utils import create_synthetic_passport_image
from data.synthetic_generator import build_td3_mrz, corrupt_mrz


def test_pipeline_genuine_passport(genuine_td3_mrz):
    """Test full pipeline execution on a clean genuine passport."""
    line1, line2 = genuine_td3_mrz
    mock_engine = MockOCREngine([
        OCRLine(text="REPUBLIC OF UTOPIA", confidence=0.99),
        OCRLine(text=line1, confidence=0.96),
        OCRLine(text=line2, confidence=0.95),
    ])

    pipeline = VerificationPipeline(ocr_engine=mock_engine)
    dummy_img = np.zeros((800, 1200, 3), dtype=np.uint8)
    response = pipeline.process_image(dummy_img)

    assert response.success is True
    assert response.mrz_present is True
    assert response.identity is not None
    assert response.identity.surname == "ERIKSSON"
    assert response.identity.given_names == "ANNA MARIA"
    assert response.identity.passport_number == "L898902C3"
    assert response.mrz_validation.overall is True
    assert response.risk.checksum_invalid is False
    assert response.risk.tampering_detected is False


def test_pipeline_ocr_character_substitution(genuine_td3_mrz):
    """Verify controlled OCR error recovery with audit record.

    Inject 'O' instead of '0' in Date of Birth (YYMMDD), e.g. '74O812'.
    The corrector should resolve this and record the correction.
    """
    line1, line2 = genuine_td3_mrz
    # Replace '0' in DOB (position 15) with 'O'
    corrupted_l2 = line2[:15] + 'O' + line2[16:]

    mock_engine = MockOCREngine([
        OCRLine(text=line1, confidence=0.96),
        OCRLine(text=corrupted_l2, confidence=0.94),
    ])

    pipeline = VerificationPipeline(ocr_engine=mock_engine)
    dummy_img = np.zeros((800, 1200, 3), dtype=np.uint8)
    response = pipeline.process_image(dummy_img)

    assert response.success is True
    assert response.mrz_present is True
    assert response.mrz_validation.overall is True

    # Ensure the correction was logged in the audit trail
    assert len(response.ocr.corrections) > 0
    dob_corrections = [c for c in response.ocr.corrections if "date_of_birth" in c.field]
    assert len(dob_corrections) >= 1
    assert dob_corrections[0].original == "O"
    assert dob_corrections[0].corrected == "0"


def test_pipeline_tampered_passport_detected(genuine_td3_mrz):
    """Verify pipeline flags tampering when passport number is forged."""
    line1, line2 = genuine_td3_mrz
    c_l1, c_l2, desc = corrupt_mrz(line1, line2, "passport_number")

    mock_engine = MockOCREngine([
        OCRLine(text=c_l1, confidence=0.96),
        OCRLine(text=c_l2, confidence=0.95),
    ])

    pipeline = VerificationPipeline(ocr_engine=mock_engine)
    dummy_img = np.zeros((800, 1200, 3), dtype=np.uint8)
    response = pipeline.process_image(dummy_img)

    assert response.success is True
    assert response.mrz_present is True
    assert response.mrz_validation.overall is False
    assert response.risk.checksum_invalid is True
    assert response.risk.tampering_detected is True
    assert any("Passport number check digit failed" in d for d in response.risk.details)


def test_pipeline_missing_mrz():
    """Verify pipeline returns failure when no MRZ exists in document."""
    mock_engine = MockOCREngine([
        OCRLine(text="RANDOM RECEIPT STORE 123", confidence=0.92),
        OCRLine(text="TOTAL AMOUNT: $45.00", confidence=0.89),
    ])

    pipeline = VerificationPipeline(ocr_engine=mock_engine)
    dummy_img = np.zeros((800, 1200, 3), dtype=np.uint8)
    response = pipeline.process_image(dummy_img)

    assert response.success is False
    assert response.mrz_present is False
    assert response.identity is None
    assert response.mrz_validation is None
    assert response.risk.checksum_invalid is True
