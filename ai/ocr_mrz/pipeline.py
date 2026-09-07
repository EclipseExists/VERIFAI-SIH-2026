"""End-to-End Passport Verification Pipeline for VERIFAI.

Coordinates:
Image Preprocessing -> OCR Engine -> MRZ Detection -> Controlled Error Correction
-> TD3 MRZ Parser -> ICAO Checksum Validation -> Risk & Tampering Analysis.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, Union, Dict, Any, List
import numpy as np

from ai.ocr_mrz.models import (
    PassportVerificationResponse,
    IdentityData,
    MRZValidationResult,
    OCRMetadata,
    RiskIndicators,
    CorrectionRecord
)
from ai.ocr_mrz.preprocessing import preprocess_for_ocr
from ai.ocr_mrz.ocr_engine import BaseOCREngine, PaddleOCREngine, get_ocr_engine
from ai.ocr_mrz.mrz_detector import MRZDetector
from ai.ocr_mrz.error_corrector import MRZErrorCorrector
from ai.ocr_mrz.mrz_parser import parse_td3_mrz
from ai.ocr_mrz.checksum import validate_td3_checksums
from ai.ocr_mrz.utils import decode_image_bytes


class VerificationPipeline:
    """Production verification pipeline for passport MRZ inspection."""

    def __init__(
        self,
        ocr_engine: Optional[BaseOCREngine] = None,
        mrz_detector: Optional[MRZDetector] = None,
        error_corrector: Optional[MRZErrorCorrector] = None
    ):
        self.ocr_engine = ocr_engine or PaddleOCREngine()
        self.mrz_detector = mrz_detector or MRZDetector()
        self.error_corrector = error_corrector or MRZErrorCorrector()

    def assess_risk(
        self,
        mrz_present: bool,
        validation: Optional[MRZValidationResult],
        identity: Optional[IdentityData],
        corrections: List[CorrectionRecord],
        avg_confidence: float
    ) -> RiskIndicators:
        """Evaluate document risk and potential tampering signals."""
        risk_flags: List[str] = []
        checksum_invalid = False
        mrz_corrupted = False
        tampering_detected = False

        if not mrz_present:
            return RiskIndicators(
                checksum_invalid=True,
                mrz_corrupted=True,
                tampering_detected=True,
                details=["No valid Machine Readable Zone (MRZ) could be identified."]
            )

        if validation:
            if not validation.overall:
                checksum_invalid = True
                if not validation.passport_number:
                    risk_flags.append("Passport number check digit failed validation.")
                if not validation.date_of_birth:
                    risk_flags.append("Date of birth check digit failed validation.")
                if not validation.expiry_date:
                    risk_flags.append("Expiry date check digit failed validation.")
                if not validation.final:
                    risk_flags.append("Composite check digit failed validation (high tampering risk).")
                    tampering_detected = True

        # Date consistency check
        if identity and identity.date_of_birth and identity.expiry_date:
            try:
                dob = datetime.strptime(identity.date_of_birth, "%Y-%m-%d")
                exp = datetime.strptime(identity.expiry_date, "%Y-%m-%d")
                if exp <= dob:
                    risk_flags.append("Logical error: Expiry date precedes Date of Birth.")
                    tampering_detected = True
                if dob > datetime.now():
                    risk_flags.append("Logical error: Date of Birth is in the future.")
                    tampering_detected = True
            except Exception:
                pass

        if avg_confidence < 0.60:
            risk_flags.append(f"Low OCR confidence ({avg_confidence:.2f}). Verification reliability reduced.")

        if len(corrections) > 4:
            risk_flags.append(f"High number of character substitutions required ({len(corrections)}).")

        if checksum_invalid or tampering_detected:
            mrz_corrupted = True

        return RiskIndicators(
            checksum_invalid=checksum_invalid,
            mrz_corrupted=mrz_corrupted,
            tampering_detected=tampering_detected,
            details=risk_flags
        )

    def process_image(self, image: np.ndarray) -> PassportVerificationResponse:
        """Run complete verification pipeline on an OpenCV image array."""
        if image is None or image.size == 0:
            return PassportVerificationResponse(
                success=False,
                mrz_present=False,
                risk=RiskIndicators(
                    checksum_invalid=True,
                    mrz_corrupted=True,
                    tampering_detected=False,
                    details=["Empty or invalid image provided."]
                )
            )

        # 1. Non-destructive Image Preprocessing
        preprocessed = preprocess_for_ocr(image)

        # 2. OCR Execution
        # First attempt OCR on contrast-enhanced full deskewed image
        ocr_lines = self.ocr_engine.detect_text(preprocessed["gray"])

        # If few or no lines detected, try binarized or dedicated MRZ crop
        if len(ocr_lines) < 2:
            crop_lines = self.ocr_engine.detect_text(preprocessed["mrz_roi"])
            if crop_lines:
                ocr_lines.extend(crop_lines)

        # 3. MRZ Detection & Scoring
        detection_result = self.mrz_detector.detect_from_ocr_lines(ocr_lines)

        if not detection_result.mrz_present or not detection_result.line1 or not detection_result.line2:
            risk_info = self.assess_risk(
                mrz_present=False,
                validation=None,
                identity=None,
                corrections=[],
                avg_confidence=0.0
            )
            return PassportVerificationResponse(
                success=False,
                mrz_present=False,
                risk=risk_info,
                ocr=OCRMetadata(
                    confidence=detection_result.confidence,
                    lines_detected=len(ocr_lines),
                    corrections=[]
                )
            )

        # 4. Controlled OCR Normalization & Correction
        norm_line1, norm_line2, corrections = self.error_corrector.process(
            detection_result.line1, detection_result.line2
        )

        # 5. TD3 MRZ Parsing
        try:
            identity = parse_td3_mrz(norm_line1, norm_line2)
        except Exception as e:
            risk_info = self.assess_risk(
                mrz_present=True,
                validation=None,
                identity=None,
                corrections=corrections,
                avg_confidence=detection_result.confidence
            )
            risk_info.details.append(f"Parsing failure: {str(e)}")
            return PassportVerificationResponse(
                success=False,
                mrz_present=True,
                risk=risk_info,
                ocr=OCRMetadata(
                    confidence=detection_result.confidence,
                    lines_detected=len(ocr_lines),
                    corrections=corrections
                ),
                raw_mrz={"line1": norm_line1, "line2": norm_line2}
            )

        # 6. ICAO Checksum Validation
        validation_result = validate_td3_checksums(norm_line2)

        # 7. Risk & Tampering Assessment
        risk_info = self.assess_risk(
            mrz_present=True,
            validation=validation_result,
            identity=identity,
            corrections=corrections,
            avg_confidence=detection_result.confidence
        )

        ocr_meta = OCRMetadata(
            confidence=detection_result.confidence,
            lines_detected=len(ocr_lines),
            corrections=corrections
        )

        return PassportVerificationResponse(
            success=True,
            mrz_present=True,
            identity=identity,
            mrz_validation=validation_result,
            ocr=ocr_meta,
            risk=risk_info,
            raw_mrz={"line1": norm_line1, "line2": norm_line2}
        )

    def process_bytes(self, image_bytes: bytes) -> PassportVerificationResponse:
        """Convenience method to process raw uploaded file bytes."""
        try:
            image = decode_image_bytes(image_bytes)
        except Exception as e:
            return PassportVerificationResponse(
                success=False,
                mrz_present=False,
                risk=RiskIndicators(
                    checksum_invalid=True,
                    mrz_corrupted=True,
                    tampering_detected=False,
                    details=[f"Image decode error: {str(e)}"]
                )
            )
        return self.process_image(image)

    def process_path(self, image_path: Union[str, Path]) -> PassportVerificationResponse:
        """Process an image loaded directly from a filesystem path."""
        p = Path(image_path)
        if not p.exists() or not p.is_file():
            return PassportVerificationResponse(
                success=False,
                mrz_present=False,
                risk=RiskIndicators(
                    checksum_invalid=True,
                    mrz_corrupted=True,
                    tampering_detected=False,
                    details=[f"File not found: {str(p)}"]
                )
            )
        try:
            with open(p, "rb") as f:
                image_bytes = f.read()
            return self.process_bytes(image_bytes)
        except Exception as e:
            return PassportVerificationResponse(
                success=False,
                mrz_present=False,
                risk=RiskIndicators(
                    checksum_invalid=True,
                    mrz_corrupted=True,
                    tampering_detected=False,
                    details=[f"Error reading image file {str(p)}: {str(e)}"]
                )
            )


_default_pipeline: Optional[VerificationPipeline] = None


def get_pipeline(engine_type: str = "paddle", **kwargs) -> VerificationPipeline:
    """Factory helper returning a configured VerificationPipeline instance."""
    global _default_pipeline
    if engine_type == "paddle" and _default_pipeline is not None:
        return _default_pipeline
    ocr_engine = get_ocr_engine(engine_type=engine_type, **kwargs)
    pipeline = VerificationPipeline(ocr_engine=ocr_engine)
    if engine_type == "paddle":
        _default_pipeline = pipeline
    return pipeline


def process_passport(
    image: Union[str, Path, bytes, np.ndarray],
    engine_type: str = "paddle",
    **kwargs
) -> PassportVerificationResponse:
    """Process a passport image and extract structured identity data and MRZ validation.

    Args:
        image: File path (str/Path), raw file bytes, or OpenCV numpy array.
        engine_type: OCR engine backend ('paddle' or 'mock').

    Returns:
        PassportVerificationResponse with structured identity and checksum validation.
    """
    pipeline = get_pipeline(engine_type=engine_type, **kwargs)
    if isinstance(image, (str, Path)):
        return pipeline.process_path(image)
    elif isinstance(image, (bytes, bytearray)):
        return pipeline.process_bytes(bytes(image))
    elif isinstance(image, np.ndarray):
        return pipeline.process_image(image)
    else:
        raise ValueError(
            f"Unsupported image type: {type(image)}. Expected file path (str/Path), bytes, or np.ndarray."
        )

