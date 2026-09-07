"""MRZ Integration Parser for VERIFAI Backend.

Conforms to the backend integration contract used by backend/app/api/mrz.py.
"""

from typing import Dict, Any
from ai.ocr_mrz.pipeline import process_passport


def parse_mrz(image_path: str, engine_type: str = "paddle") -> Dict[str, Any]:
    """Parse MRZ from an image file and return structured result dictionary.

    Args:
        image_path: Path to document image.
        engine_type: OCR backend ('paddle' or 'mock').

    Returns:
        Dictionary adhering to backend MRZ data contract:
        - mrz_present: bool
        - parsed_fields: dict of holder identity fields
        - checksum_valid: bool
        - checksum_details: list of field-level checksum evaluations
        - raw_lines: list of MRZ strings
    """
    response = process_passport(image_path, engine_type=engine_type)

    if not response.mrz_present or not response.identity:
        return {
            "mrz_present": False,
            "parsed_fields": {},
            "checksum_valid": False,
            "checksum_details": [],
            "raw_lines": [],
            "_stub": False,
        }

    val = response.mrz_validation
    checksum_details = []
    if val:
        checksum_details = [
            {"field": "passport_number", "valid": val.passport_number},
            {"field": "date_of_birth", "valid": val.date_of_birth},
            {"field": "expiry_date", "valid": val.expiry_date},
            {"field": "composite", "valid": val.final},
        ]
        if val.personal_number is not None:
            checksum_details.append({"field": "personal_number", "valid": val.personal_number})

    raw_lines = []
    if response.raw_mrz:
        raw_lines = [response.raw_mrz.get("line1", ""), response.raw_mrz.get("line2", "")]

    return {
        "mrz_present": True,
        "parsed_fields": response.identity.model_dump(),
        "checksum_valid": val.overall if val else False,
        "checksum_details": checksum_details,
        "raw_lines": raw_lines,
        "_stub": False,
    }
