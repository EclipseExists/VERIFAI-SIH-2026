"""Document Validation Service.

Adapted from teammate's code. All imports self-contained within ai.risk_engine.
"""

from datetime import date
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from ai.risk_engine.core.risk_config import RiskEngineConfig, default_risk_config
from ai.risk_engine.schemas.risk import RiskSignal, SignalDirection, SourceModule
from ai.risk_engine.schemas.validation import (
    DocumentValidationInput,
    ValidationCheck,
    ValidationResult,
)
from ai.risk_engine.services.validation.date_utils import parse_date, parse_date_with_status


def is_non_empty(val: Any) -> bool:
    if val is None:
        return False
    if isinstance(val, str):
        return bool(val.strip())
    return True


def extract_field_value(input_data: DocumentValidationInput, direct_attr: Optional[str], field_aliases: List[str]) -> Optional[str]:
    if direct_attr:
        val = getattr(input_data, direct_attr, None)
        if is_non_empty(val):
            return str(val).strip()
    structured = input_data.structured_fields or {}
    for alias in field_aliases:
        if alias in structured and is_non_empty(structured[alias]):
            return str(structured[alias]).strip()
    return None


class DocumentValidationEngine:
    """Stateless deterministic document validation engine."""

    def __init__(self, config: Optional[RiskEngineConfig] = None):
        self.config = config or default_risk_config

    def validate(self, input_data: DocumentValidationInput, reference_date: Optional[date] = None) -> ValidationResult:
        ref_date = reference_date or date.today()
        checks: List[ValidationCheck] = []

        doc_num = extract_field_value(input_data, "doc_number", ["doc_number", "document_number", "passport_number"])
        raw_expiry = extract_field_value(input_data, "expiry_date", ["expiry_date", "expiry", "expiration_date"])
        raw_issue = extract_field_value(input_data, "issue_date", ["issue_date", "issue", "issuance_date"])
        raw_dob = extract_field_value(input_data, "dob", ["dob", "date_of_birth", "birth_date"])
        name_val = extract_field_value(input_data, None, ["name", "surname", "last_name", "first_name", "full_name", "given_names"])

        parsed_expiry, expiry_ok, _ = parse_date_with_status(raw_expiry, "expiry date")
        parsed_issue, issue_ok, _ = parse_date_with_status(raw_issue, "issue date")
        parsed_dob, dob_ok, _ = parse_date_with_status(raw_dob, "date of birth", is_dob=True)

        # Rule 1: expiry_not_past
        if not is_non_empty(raw_expiry) or not expiry_ok or parsed_expiry is None:
            checks.append(ValidationCheck(rule="expiry_not_past", passed=False, explanation="Document expiry date is missing or invalid."))
        elif parsed_expiry >= ref_date:
            checks.append(ValidationCheck(rule="expiry_not_past", passed=True, explanation=f"Document unexpired (expires {parsed_expiry.isoformat()})."))
        else:
            checks.append(ValidationCheck(rule="expiry_not_past", passed=False, explanation=f"Document expired on {parsed_expiry.isoformat()}."))

        # Rule 2: issue_before_expiry
        if not is_non_empty(raw_issue):
            checks.append(ValidationCheck(rule="issue_before_expiry", passed=True, explanation="Issue date not provided; skipped.", severity="minor"))
        elif issue_ok and parsed_issue and expiry_ok and parsed_expiry and parsed_issue < parsed_expiry:
            checks.append(ValidationCheck(rule="issue_before_expiry", passed=True, explanation=f"Issue date ({parsed_issue}) precedes expiry ({parsed_expiry})."))
        else:
            checks.append(ValidationCheck(rule="issue_before_expiry", passed=False, explanation="Issue date is on or after expiry date."))

        # Rule 3: dob_sanity
        if not is_non_empty(raw_dob) or not dob_ok or parsed_dob is None:
            checks.append(ValidationCheck(rule="dob_sanity", passed=False, explanation="Date of birth is missing or invalid."))
        elif parsed_dob >= ref_date:
            checks.append(ValidationCheck(rule="dob_sanity", passed=False, explanation=f"Date of birth ({parsed_dob}) is in the future."))
        elif parsed_issue and parsed_dob >= parsed_issue:
            checks.append(ValidationCheck(rule="dob_sanity", passed=False, explanation=f"Date of birth ({parsed_dob}) is after issue date ({parsed_issue})."))
        else:
            checks.append(ValidationCheck(rule="dob_sanity", passed=True, explanation=f"Date of birth ({parsed_dob}) is plausible."))

        # Rule 4: mandatory_fields_present
        missing = []
        if not is_non_empty(doc_num):
            missing.append("doc_number")
        if not is_non_empty(raw_dob):
            missing.append("dob")
        if not is_non_empty(name_val):
            missing.append("name")
        if missing:
            checks.append(ValidationCheck(rule="mandatory_fields_present", passed=False, explanation=f"Missing: {', '.join(missing)}."))
        else:
            checks.append(ValidationCheck(rule="mandatory_fields_present", passed=True, explanation="All mandatory fields present."))

        # Rule 5: doc_number_format
        if is_non_empty(doc_num):
            is_valid = self.config.validate_doc_number(doc_num, input_data.doc_type, input_data.issuing_country)
            if is_valid:
                checks.append(ValidationCheck(rule="doc_number_format", passed=True, explanation=f"Doc number '{doc_num}' format is valid."))
            else:
                checks.append(ValidationCheck(rule="doc_number_format", passed=False, explanation=f"Doc number '{doc_num}' format mismatch."))
        else:
            checks.append(ValidationCheck(rule="doc_number_format", passed=False, explanation="Doc number missing; cannot validate format."))

        overall_valid = all(c.passed for c in checks)
        return ValidationResult(document_id=input_data.document_id, case_id=input_data.case_id, is_valid=overall_valid, checks=checks)

    def to_risk_signals(self, validation_result: ValidationResult, case_id: Optional[Union[UUID, str]] = None) -> List[RiskSignal]:
        active_case_id = case_id or validation_result.case_id or "unknown-case"
        signals: List[RiskSignal] = []
        for check in validation_result.checks:
            if check.passed:
                continue
            if check.rule == "expiry_not_past":
                signal_name = "document_expired"
            elif check.rule == "issue_before_expiry":
                signal_name = "issue_after_expiry"
            elif check.rule == "dob_sanity":
                signal_name = "dob_in_future" if "future" in check.explanation else "dob_after_issue"
            elif check.rule == "mandatory_fields_present":
                signal_name = "mandatory_field_missing"
            elif check.rule == "doc_number_format":
                signal_name = "doc_number_format_mismatch"
            else:
                signal_name = f"validation_{check.rule}_failed"
            signals.append(RiskSignal(
                case_id=active_case_id, signal_name=signal_name,
                direction=SignalDirection.INCREASES_RISK, magnitude=1.0,
                explanation=check.explanation, source_module=SourceModule.VALIDATION,
            ))
        return signals
