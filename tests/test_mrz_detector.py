"""Unit tests for MRZ Detection and Multi-factor Scoring."""

import pytest
from ai.ocr_mrz.mrz_detector import MRZDetector
from ai.ocr_mrz.models import OCRLine, BoundingBox
from data.synthetic_generator import build_td3_mrz


@pytest.fixture
def detector():
    return MRZDetector(min_confidence_threshold=0.65)


def test_reject_arbitrary_long_text(detector):
    """Verify that text merely longer than 40 chars without MRZ features is rejected."""
    arbitrary_text = [
        OCRLine(
            text="THIS IS A STANDARD LEGAL DISCLAIMER SENTENCE THAT EXCEEDS FORTY CHARACTERS EASILY",
            confidence=0.95
        ),
        OCRLine(
            text="ANOTHER VERY LONG LINE OF TEXT THAT IS DEFINITELY NOT A MACHINE READABLE PASSPORT ZONE",
            confidence=0.92
        )
    ]

    res = detector.detect_from_ocr_lines(arbitrary_text)
    assert res.mrz_present is False
    assert res.confidence < 0.50


def test_detect_genuine_mrz(detector, genuine_td3_mrz):
    """Verify that a genuine TD3 MRZ is detected with high confidence."""
    line1, line2 = genuine_td3_mrz
    ocr_lines = [
        OCRLine(
            text="PASSPORT REPUBLIC OF UTOPIA",
            bounding_box=BoundingBox(points=[[50, 50], [400, 50], [400, 80], [50, 80]]),
            confidence=0.99
        ),
        OCRLine(
            text="SURNAME: ERIKSSON GIVEN NAMES: ANNA MARIA",
            bounding_box=BoundingBox(points=[[50, 100], [500, 100], [500, 130], [50, 130]]),
            confidence=0.97
        ),
        OCRLine(
            text=line1,
            bounding_box=BoundingBox(points=[[50, 500], [1000, 500], [1000, 530], [50, 530]]),
            confidence=0.96
        ),
        OCRLine(
            text=line2,
            bounding_box=BoundingBox(points=[[50, 540], [1000, 540], [1000, 570], [50, 570]]),
            confidence=0.95
        )
    ]

    res = detector.detect_from_ocr_lines(ocr_lines)
    assert res.mrz_present is True
    assert res.confidence >= 0.70
    assert res.line1 == line1
    assert res.line2 == line2


def test_missing_mrz(detector):
    """Verify response when no OCR lines are provided."""
    res = detector.detect_from_ocr_lines([])
    assert res.mrz_present is False
    assert res.confidence == 0.0
    assert res.line1 is None
    assert res.line2 is None


def test_scoring_weights(detector, genuine_td3_mrz):
    """Verify that score_line yields high values for Line 1 and Line 2 components."""
    line1, line2 = genuine_td3_mrz

    s1, bd1 = detector.score_line(line1, is_line1=True)
    assert s1 >= 0.75
    assert bd1["length"] == 1.0
    assert bd1["purity"] == 1.0
    assert bd1["structure"] >= 0.8

    s2, bd2 = detector.score_line(line2, is_line1=False)
    assert s2 >= 0.75
    assert bd2["length"] == 1.0
    assert bd2["purity"] == 1.0
