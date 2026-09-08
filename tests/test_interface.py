"""Tests for top-level ocr_mrz public interface, CLI runner, and backend bridges."""

import sys
import subprocess
from pathlib import Path
import pytest
import cv2
import numpy as np

from ocr_mrz import (
    process_passport,
    PassportVerificationResponse,
    IdentityData,
    MRZValidationResult,
    RiskIndicators,
)
from ai.mrz.parse import parse_mrz
from ai.ocr.extract import run_ocr
from ai.ocr_mrz.ocr_engine import MockOCREngine
from ai.ocr_mrz.models import OCRLine
from data.synthetic_generator import build_td3_mrz
from ai.ocr_mrz.utils import create_synthetic_passport_image


@pytest.fixture
def genuine_passport_path(tmp_path, genuine_td3_mrz):
    """Create a temporary genuine passport image file for testing."""
    line1, line2 = genuine_td3_mrz
    img = create_synthetic_passport_image(line1, line2)
    path = tmp_path / "test_passport_genuine.png"
    cv2.imwrite(str(path), img)
    return str(path)


def test_process_passport_from_path(genuine_passport_path):
    """Verify process_passport accepts a file path string."""
    # Run with mock engine for speed and deterministic testing
    result = process_passport(genuine_passport_path, engine_type="mock")

    assert isinstance(result, PassportVerificationResponse)
    assert result.success is True
    assert result.mrz_present is True
    assert result.identity is not None
    assert result.identity.passport_number == "L898902C3"
    assert result.identity.surname == "ERIKSSON"
    assert result.mrz_validation.overall is True


def test_process_passport_from_bytes(genuine_passport_path):
    """Verify process_passport accepts raw file bytes."""
    with open(genuine_passport_path, "rb") as f:
        img_bytes = f.read()

    result = process_passport(img_bytes, engine_type="mock")
    assert result.success is True
    assert result.mrz_present is True
    assert result.identity.passport_number == "L898902C3"


def test_process_passport_from_numpy_array(genuine_passport_path):
    """Verify process_passport accepts an OpenCV numpy array."""
    img = cv2.imread(genuine_passport_path)
    result = process_passport(img, engine_type="mock")
    assert result.success is True
    assert result.mrz_present is True
    assert result.identity.passport_number == "L898902C3"


def test_process_passport_missing_file():
    """Verify process_passport returns safe failure on nonexistent file path."""
    result = process_passport("non_existent_file_path_12345.jpg")
    assert result.success is False
    assert result.mrz_present is False
    assert any("File not found" in d for d in result.risk.details)


def test_backend_bridge_parse_mrz(genuine_passport_path):
    """Verify backend bridge ai.mrz.parse.parse_mrz conforms to backend contract."""
    data = parse_mrz(genuine_passport_path, engine_type="mock")

    assert data["mrz_present"] is True
    assert data["checksum_valid"] is True
    assert isinstance(data["parsed_fields"], dict)
    assert data["parsed_fields"]["passport_number"] == "L898902C3"
    assert len(data["checksum_details"]) >= 4
    assert data["_stub"] is False


def test_backend_bridge_run_ocr(genuine_passport_path):
    """Verify backend bridge ai.ocr.extract.run_ocr conforms to backend contract."""
    data = run_ocr(genuine_passport_path, engine_type="mock")

    assert isinstance(data["structured_fields"], dict)
    assert data["structured_fields"]["doc_number"] == "L898902C3"
    assert data["structured_fields"]["name"] == "ERIKSSON ANNA MARIA"
    assert "doc_number" in data["field_confidence"]
    assert len(data["raw_text"]) > 0
    assert data["_stub"] is False


def test_cli_runner_execution(genuine_passport_path):
    """Verify standalone CLI module execution via python -m ocr_mrz.cli."""
    res = subprocess.run(
        [sys.executable, "-m", "ocr_mrz.cli", genuine_passport_path, "--mock"],
        capture_output=True,
        text=True
    )
    assert res.returncode == 0
    assert "VERIFICATION RESULT" in res.stdout
    assert "Holder Name:" in res.stdout
    assert "ERIKSSON" in res.stdout
    assert "Checksum Valid:  True" in res.stdout
