"""Pytest test fixtures for VERIFAI test suite."""

import pytest
from ai.ocr_mrz.models import OCRLine, BoundingBox
from ai.ocr_mrz.ocr_engine import MockOCREngine
from data.synthetic_generator import build_td3_mrz, corrupt_mrz


@pytest.fixture
def genuine_td3_mrz():
    """Returns a valid 2-line TD3 synthetic MRZ."""
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
    return line1, line2


@pytest.fixture
def mock_ocr_engine(genuine_td3_mrz):
    """Returns a MockOCREngine with genuine MRZ lines."""
    line1, line2 = genuine_td3_mrz
    lines = [
        OCRLine(
            text="REPUBLIC OF UTOPIA PASSPORT",
            bounding_box=BoundingBox(points=[[50, 50], [500, 50], [500, 80], [50, 80]]),
            confidence=0.98
        ),
        OCRLine(
            text=line1,
            bounding_box=BoundingBox(points=[50, 600], points2=[1100, 600], points3=[1100, 630], points4=[50, 630]) if False else BoundingBox(points=[[50, 600], [1100, 600], [1100, 630], [50, 630]]),
            confidence=0.96
        ),
        OCRLine(
            text=line2,
            bounding_box=BoundingBox(points=[[50, 640], [1100, 640], [1100, 670], [50, 670]]),
            confidence=0.95
        )
    ]
    return MockOCREngine(lines)
