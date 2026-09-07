"""Data models for VERIFAI OCR + MRZ subsystem."""

from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Bounding box coordinates [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]."""
    points: List[List[float]] = Field(
        default_factory=list,
        description="4 corner points of bounding polygon: top-left, top-right, bottom-right, bottom-left"
    )

    @property
    def x_min(self) -> float:
        return min(p[0] for p in self.points) if self.points else 0.0

    @property
    def x_max(self) -> float:
        return max(p[0] for p in self.points) if self.points else 0.0

    @property
    def y_min(self) -> float:
        return min(p[1] for p in self.points) if self.points else 0.0

    @property
    def y_max(self) -> float:
        return max(p[1] for p in self.points) if self.points else 0.0

    @property
    def width(self) -> float:
        return self.x_max - self.x_min

    @property
    def height(self) -> float:
        return self.y_max - self.y_min


class OCRLine(BaseModel):
    """A single recognized line from OCR."""
    text: str = Field(..., description="Recognized text string")
    bounding_box: Optional[BoundingBox] = Field(default=None, description="Bounding polygon")
    confidence: float = Field(..., ge=0.0, le=1.0, description="OCR confidence score (0.0 to 1.0)")


class CorrectionRecord(BaseModel):
    """Audit trail record for an OCR correction applied to the MRZ."""
    field: str = Field(..., description="Field name or character index")
    original: str = Field(..., description="Raw text as extracted by OCR")
    corrected: str = Field(..., description="Normalized or corrected character/string")
    reason: str = Field(..., description="Justification (e.g., 'checksum-supported correction')")


class MRZDetectionResult(BaseModel):
    """Result of MRZ detection."""
    mrz_present: bool = Field(..., description="Whether a valid MRZ block was detected")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    line1: Optional[str] = Field(default=None, description="MRZ Line 1 (approx 44 characters)")
    line2: Optional[str] = Field(default=None, description="MRZ Line 2 (approx 44 characters)")
    raw_candidates: Optional[List[str]] = Field(default=None, description="Raw candidate lines before cleanup")
    score_breakdown: Optional[Dict[str, float]] = Field(default=None, description="Detailed scoring criteria")


class IdentityData(BaseModel):
    """Structured holder identity extracted from passport MRZ."""
    name: str = Field(..., description="Full formatted name: SURNAME GIVEN NAMES")
    surname: str = Field(..., description="Holder surname/primary identifier")
    given_names: str = Field(..., description="Holder given names/secondary identifier")
    passport_number: str = Field(..., description="Passport/document number")
    nationality: str = Field(..., description="3-letter nationality code (ICAO Doc 9303)")
    issuing_state: str = Field(..., description="3-letter issuing state code")
    date_of_birth: Optional[str] = Field(default=None, description="ISO format date: YYYY-MM-DD")
    raw_date_of_birth: str = Field(..., description="Raw YYMMDD from MRZ")
    sex: str = Field(..., description="Sex: M, F, or X/unspecified")
    expiry_date: Optional[str] = Field(default=None, description="ISO format date: YYYY-MM-DD")
    raw_expiry_date: str = Field(..., description="Raw YYMMDD from MRZ")
    personal_number: Optional[str] = Field(default=None, description="Optional personal or national ID number")
    document_type: str = Field(default="P", description="Document type code")


class MRZValidationResult(BaseModel):
    """ICAO 9303 checksum validation outcomes."""
    passport_number: bool = Field(..., description="Passport number check digit valid")
    date_of_birth: bool = Field(..., description="Date of birth check digit valid")
    expiry_date: bool = Field(..., description="Expiry date check digit valid")
    personal_number: Optional[bool] = Field(default=None, description="Personal number check digit valid (if present)")
    final: bool = Field(..., description="Composite check digit valid")
    overall: bool = Field(..., description="All applicable check digits valid")


class OCRMetadata(BaseModel):
    """OCR performance and execution metadata."""
    confidence: float = Field(..., ge=0.0, le=1.0, description="Average OCR confidence across MRZ lines")
    lines_detected: int = Field(default=0, description="Total text lines extracted by OCR")
    corrections: List[CorrectionRecord] = Field(default_factory=list, description="Audit log of all corrections applied")


class RiskIndicators(BaseModel):
    """Risk and potential tampering indicators."""
    checksum_invalid: bool = Field(..., description="True if one or more checksums failed")
    mrz_corrupted: bool = Field(..., description="True if MRZ format/characters are irregular")
    tampering_detected: bool = Field(default=False, description="True if evidence suggests document alteration")
    details: List[str] = Field(default_factory=list, description="Descriptive risk flags and warnings")


class PassportVerificationResponse(BaseModel):
    """Complete production response model for passport verification."""
    success: bool = Field(..., description="True if document was processed successfully")
    mrz_present: bool = Field(..., description="True if MRZ was located and extracted")
    identity: Optional[IdentityData] = Field(default=None, description="Parsed identity fields")
    mrz_validation: Optional[MRZValidationResult] = Field(default=None, description="Checksum validation report")
    ocr: Optional[OCRMetadata] = Field(default=None, description="OCR confidence and correction audit trail")
    risk: RiskIndicators = Field(..., description="Security and tampering risk assessment")
    raw_mrz: Optional[Dict[str, str]] = Field(default=None, description="Raw normalized MRZ lines")
