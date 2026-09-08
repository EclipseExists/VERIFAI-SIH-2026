"""OCR Extraction Integration for VERIFAI Backend.

Conforms to the backend integration contract used by backend/app/api/ocr.py.
"""

from typing import Dict, Any
from ai.ocr_mrz.pipeline import process_passport


def run_ocr(image_path: str, engine_type: str = "paddle") -> Dict[str, Any]:
    """Run OCR extraction and field mapping for backend document processing.

    Args:
        image_path: Path to passport/document image.
        engine_type: OCR backend ('paddle' or 'mock').

    Returns:
        Dictionary adhering to backend OCR data contract:
        - structured_fields: dict (name, dob, doc_number, nationality, expiry)
        - field_confidence: dict of per-field confidence scores
        - raw_text: extracted raw text representation
        - _stub: bool
    """
    response = process_passport(image_path, engine_type=engine_type)

    if not response.success or not response.identity:
        return {
            "structured_fields": {},
            "field_confidence": {},
            "raw_text": "",
            "_stub": False,
        }

    ident = response.identity
    conf = response.ocr.confidence if response.ocr else 0.90

    raw_text = ""
    if response.raw_mrz:
        raw_text = f"{response.raw_mrz.get('line1', '')}\n{response.raw_mrz.get('line2', '')}"

    structured = {
        "name": ident.name,
        "dob": ident.date_of_birth,
        "doc_number": ident.passport_number,
        "nationality": ident.nationality,
        "expiry": ident.expiry_date,
        "sex": ident.sex,
        "issuing_state": ident.issuing_state,
    }

    confidence_dict = {
        "name": conf,
        "dob": conf,
        "doc_number": conf,
        "nationality": conf,
        "expiry": conf,
    }

    return {
        "structured_fields": structured,
        "field_confidence": confidence_dict,
        "raw_text": raw_text,
        "_stub": False,
    }
