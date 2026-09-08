"""VERIFAI OCR + MRZ Subsystem.

Provides end-to-end OCR processing, MRZ detection, TD3 parsing,
ICAO 9303 checksum validation, and risk analysis for passport verification.
"""

from ai.ocr_mrz.models import (
    PassportVerificationResponse,
    IdentityData,
    MRZValidationResult,
    OCRMetadata,
    RiskIndicators,
    CorrectionRecord,
    OCRLine,
    BoundingBox,
    MRZDetectionResult,
)
from ai.ocr_mrz.checksum import (
    calculate_check_digit,
    validate_check_digit,
    validate_td3_checksums,
    char_to_value,
    ICAO_WEIGHTS,
)
from ai.ocr_mrz.preprocessing import (
    resize_image,
    to_grayscale,
    enhance_contrast_clahe,
    denoise_image,
    binarize_adaptive,
    binarize_otsu,
    detect_and_deskew,
    preprocess_for_ocr,
)
from ai.ocr_mrz.ocr_engine import (
    BaseOCREngine,
    PaddleOCREngine,
    MockOCREngine,
    get_ocr_engine,
)
from ai.ocr_mrz.mrz_detector import MRZDetector
from ai.ocr_mrz.error_corrector import MRZErrorCorrector
from ai.ocr_mrz.mrz_parser import parse_td3_mrz, parse_mrz_date
from ai.ocr_mrz.pipeline import VerificationPipeline, process_passport, get_pipeline
from ai.ocr_mrz.utils import decode_image_bytes, create_synthetic_passport_image

__all__ = [
    "PassportVerificationResponse",
    "IdentityData",
    "MRZValidationResult",
    "OCRMetadata",
    "RiskIndicators",
    "CorrectionRecord",
    "OCRLine",
    "BoundingBox",
    "MRZDetectionResult",
    "calculate_check_digit",
    "validate_check_digit",
    "validate_td3_checksums",
    "char_to_value",
    "ICAO_WEIGHTS",
    "resize_image",
    "to_grayscale",
    "enhance_contrast_clahe",
    "denoise_image",
    "binarize_adaptive",
    "binarize_otsu",
    "detect_and_deskew",
    "preprocess_for_ocr",
    "BaseOCREngine",
    "PaddleOCREngine",
    "MockOCREngine",
    "get_ocr_engine",
    "MRZDetector",
    "MRZErrorCorrector",
    "parse_td3_mrz",
    "parse_mrz_date",
    "VerificationPipeline",
    "process_passport",
    "get_pipeline",
    "decode_image_bytes",
    "create_synthetic_passport_image",
]
