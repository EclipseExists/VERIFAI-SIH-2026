"""VERIFAI OCR + MRZ Module.

Minimal, clean entrypoint for passport OCR and MRZ parsing/validation.

Standard Usage:
    from ocr_mrz import process_passport

    result = process_passport("passport.jpg")
    if result.mrz_present:
        print("Holder:", result.identity.name)
        print("Passport Number:", result.identity.passport_number)
        print("Checksum Valid:", result.mrz_validation.overall)
"""

from ai.ocr_mrz import (
    process_passport,
    get_pipeline,
    VerificationPipeline,
    PassportVerificationResponse,
    IdentityData,
    MRZValidationResult,
    OCRMetadata,
    RiskIndicators,
    CorrectionRecord,
    OCRLine,
    BoundingBox,
    MRZDetectionResult,
    calculate_check_digit,
    validate_check_digit,
    validate_td3_checksums,
    char_to_value,
    ICAO_WEIGHTS,
    resize_image,
    to_grayscale,
    enhance_contrast_clahe,
    denoise_image,
    binarize_adaptive,
    binarize_otsu,
    detect_and_deskew,
    preprocess_for_ocr,
    BaseOCREngine,
    PaddleOCREngine,
    MockOCREngine,
    get_ocr_engine,
    MRZDetector,
    MRZErrorCorrector,
    parse_td3_mrz,
    parse_mrz_date,
    decode_image_bytes,
    create_synthetic_passport_image,
)

__all__ = [
    "process_passport",
    "get_pipeline",
    "VerificationPipeline",
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
    "decode_image_bytes",
    "create_synthetic_passport_image",
]
