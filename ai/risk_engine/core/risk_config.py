"""Risk Engine Configuration.

Adapted from teammate's code. All imports are self-contained within ai.risk_engine.
"""

import re
from typing import Dict, Optional
from pydantic import BaseModel, Field

from ai.risk_engine.schemas.risk import RiskBand


# Signal Weights — positive = increases risk, negative = decreases risk
DEFAULT_SIGNAL_WEIGHTS: Dict[str, float] = {
    "mrz_checksum_mismatch": 30.0,
    "mrz_checksum_failure": 30.0,
    "document_expired": 25.0,
    "dob_mismatch": 20.0,
    "cross_doc_dob_mismatch": 20.0,
    "forensic_anomaly": 15.0,
    "forensic_anomaly_detected": 15.0,
    "face_mismatch": 30.0,
    "good_document_quality": -5.0,
    "quality_check_passed": -5.0,
    "issue_after_expiry": 20.0,
    "dob_in_future": 20.0,
    "dob_after_issue": 20.0,
    "mandatory_field_missing": 15.0,
    "doc_number_format_mismatch": 15.0,
    "expiry_date_missing": 10.0,
    "name_mismatch": 10.0,
    "mrz_missing": 10.0,
    "mrz_visual_mismatch": 15.0,
    "face_match_uncertain": 10.0,
    "default": 10.0,
}

LOW_RISK_MAX_THRESHOLD: float = 30.0
HIGH_RISK_MIN_THRESHOLD: float = 70.0

# Document number regex patterns
DEFAULT_DOC_NUMBER_PATTERNS: Dict[str, str] = {
    "passport": r"^[A-Z0-9<]{8,9}$",
    "passport_ind": r"^[A-Z][0-9]{7}$",
    "passport_usa": r"^[0-9]{9}$",
    "passport_gbr": r"^[0-9]{9}$",
    "visa": r"^[A-Z0-9]{8,12}$",
    "id_card": r"^[A-Z0-9]{6,14}$",
    "permit": r"^[A-Z0-9]{6,12}$",
    "generic": r"^[A-Z0-9]{5,15}$",
}


class RiskEngineConfig(BaseModel):
    """Runtime-configurable settings for the Risk Engine."""

    weights: Dict[str, float] = Field(default_factory=lambda: DEFAULT_SIGNAL_WEIGHTS.copy())
    low_threshold: float = Field(default=LOW_RISK_MAX_THRESHOLD)
    high_threshold: float = Field(default=HIGH_RISK_MIN_THRESHOLD)
    min_score: float = Field(default=0.0)
    max_score: float = Field(default=100.0)
    doc_number_patterns: Dict[str, str] = Field(default_factory=lambda: DEFAULT_DOC_NUMBER_PATTERNS.copy())

    def get_weight(self, signal_name: str) -> float:
        normalized = signal_name.strip().lower()
        return self.weights.get(normalized, self.weights.get("default", 10.0))

    def get_risk_band(self, score: float) -> RiskBand:
        if score < self.low_threshold:
            return RiskBand.LOW
        elif score < self.high_threshold:
            return RiskBand.MEDIUM
        return RiskBand.HIGH

    def get_doc_pattern(self, doc_type: str, country: Optional[str] = None) -> Optional[str]:
        normalized_type = doc_type.strip().lower()
        if country:
            country_key = f"{normalized_type}_{country.strip().lower()}"
            if country_key in self.doc_number_patterns:
                return self.doc_number_patterns[country_key]
        if normalized_type in self.doc_number_patterns:
            return self.doc_number_patterns[normalized_type]
        return self.doc_number_patterns.get("generic")

    def validate_doc_number(self, doc_number: str, doc_type: str, country: Optional[str] = None) -> bool:
        pattern = self.get_doc_pattern(doc_type, country)
        if not pattern:
            return True
        return bool(re.match(pattern, doc_number.strip().upper()))


default_risk_config = RiskEngineConfig()
