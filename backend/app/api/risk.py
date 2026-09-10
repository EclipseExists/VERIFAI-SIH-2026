"""
VERIFAI — Risk Assessment Engine (Integrated)
================================================

POST /api/v1/cases/{case_id}/risk-assessment

Combines:
1. Our hardcoded signal collection (OCR, MRZ, face, forensics readings from DB)
2. Teammate's RiskEngine for weighted scoring
3. Teammate's DocumentValidationEngine for date/field validation
4. Database storage for audit trail

The officer sees: score (0-100), band (low/medium/high), and every signal explained.
"""

import sys
import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.case import Case
from app.schemas.risk import RiskAssessmentOut

router = APIRouter()
PLACEHOLDER_OFFICER_ID = UUID("00000000-0000-0000-0000-000000000001")

# Add project root for ai/ imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _collect_signals(case_id, mrz_result, ocr_result, face_result, forensics_result):
    """
    Collect risk signals from all AI module results stored in the database.

    Each signal is a plain dict that maps directly to the RiskSignal DB model.
    Uses the teammate's RiskEngine for final scoring.
    """
    signals = []

    # ── Cross-Field Consistency (VIZ vs MRZ) ───────────────────────
    has_cross_mismatch = False
    if (
        ocr_result
        and not ocr_result.is_stub
        and ocr_result.structured_fields
        and mrz_result
        and not mrz_result.is_stub
        and mrz_result.mrz_present
        and mrz_result.parsed_fields
    ):
        ocr_fields = ocr_result.structured_fields
        mrz_fields = mrz_result.parsed_fields

        # 1. DOB Consistency
        ocr_dob = ocr_fields.get("dob")
        mrz_dob = mrz_fields.get("date_of_birth")
        if ocr_dob and mrz_dob and str(ocr_dob).strip() != str(mrz_dob).strip():
            has_cross_mismatch = True
            signals.append({
                "signal_name": "dob_mismatch",
                "direction": "increases_risk",
                "magnitude": 1.0,
                "explanation": (
                    f"Visual Inspection Zone DOB ({ocr_dob}) does not match "
                    f"MRZ encoded DOB ({mrz_dob}). Strong indicator of visual tampering or invalid MRZ."
                ),
                "source_module": "consistency",
            })
            signals.append({
                "signal_name": "mrz_visual_mismatch",
                "direction": "increases_risk",
                "magnitude": 1.0,
                "explanation": (
                    f"Conflicting birth dates between visual zone ({ocr_dob}) and MRZ ({mrz_dob})."
                ),
                "source_module": "consistency",
            })

        # 2. Document Number Consistency
        ocr_doc = (ocr_fields.get("doc_number") or "").replace("<", "").strip().upper()
        mrz_doc = (mrz_fields.get("passport_number") or "").replace("<", "").strip().upper()
        if ocr_doc and mrz_doc and ocr_doc != mrz_doc:
            has_cross_mismatch = True
            signals.append({
                "signal_name": "mrz_visual_mismatch",
                "direction": "increases_risk",
                "magnitude": 1.0,
                "explanation": (
                    f"Visual document number ({ocr_doc}) does not match "
                    f"MRZ passport number ({mrz_doc})."
                ),
                "source_module": "consistency",
            })

        # 3. Expiry Date Consistency
        ocr_exp = ocr_fields.get("expiry")
        mrz_exp = mrz_fields.get("expiry_date")
        if ocr_exp and mrz_exp and str(ocr_exp).strip() != str(mrz_exp).strip():
            has_cross_mismatch = True
            signals.append({
                "signal_name": "mrz_visual_mismatch",
                "direction": "increases_risk",
                "magnitude": 1.0,
                "explanation": (
                    f"Visual expiry date ({ocr_exp}) does not match "
                    f"MRZ expiry date ({mrz_exp})."
                ),
                "source_module": "consistency",
            })

    # ── MRZ Signals ────────────────────────────────────────────────
    if mrz_result and not mrz_result.is_stub:
        if not mrz_result.mrz_present:
            signals.append({
                "signal_name": "mrz_missing",
                "direction": "increases_risk",
                "magnitude": 1.0,
                "explanation": "No Machine-Readable Zone (MRZ) detected on the document.",
                "source_module": "mrz",
            })
        elif mrz_result.checksum_valid is False:
            signals.append({
                "signal_name": "mrz_checksum_failure",
                "direction": "increases_risk",
                "magnitude": 1.0,
                "explanation": (
                    "MRZ checksum validation failed. Per ICAO 9303, this indicates "
                    "the document data may have been altered."
                ),
                "source_module": "mrz",
            })
        elif mrz_result.checksum_valid is True:
            if not has_cross_mismatch:
                signals.append({
                    "signal_name": "quality_check_passed",
                    "direction": "decreases_risk",
                    "magnitude": 1.0,
                    "explanation": "All MRZ checksums validated. Document data is internally consistent.",
                    "source_module": "mrz",
                })

    # ── Face Verification Signals ──────────────────────────────────
    if face_result:
        if face_result.band == "mismatch":
            signals.append({
                "signal_name": "face_mismatch",
                "direction": "increases_risk",
                "magnitude": 1.0,
                "explanation": (
                    f"Face similarity score {face_result.similarity_score:.2f} — "
                    "below mismatch threshold. Person's face does not match the document photo."
                ),
                "source_module": "face",
            })
        elif face_result.band == "uncertain":
            signals.append({
                "signal_name": "face_match_uncertain",
                "direction": "increases_risk",
                "magnitude": 1.0,
                "explanation": (
                    f"Face similarity score {face_result.similarity_score:.2f} — uncertain zone. "
                    "Officer should manually compare faces."
                ),
                "source_module": "face",
            })
        elif face_result.band == "match":
            signals.append({
                "signal_name": "good_document_quality",
                "direction": "decreases_risk",
                "magnitude": 1.0,
                "explanation": (
                    f"Face similarity score {face_result.similarity_score:.2f} — match. "
                    "Person's face matches the document photo."
                ),
                "source_module": "face",
            })
        elif face_result.band == "error":
            signals.append({
                "signal_name": "face_mismatch",
                "direction": "increases_risk",
                "magnitude": 0.5,
                "explanation": "Face could not be detected in one of the images. Re-capture recommended.",
                "source_module": "face",
            })

    # ── Forensics Signals ──────────────────────────────────────────
    if forensics_result and not forensics_result.is_stub:
        prob = forensics_result.overall_manipulation_probability
        if prob is not None:
            if prob >= 0.7:
                signals.append({
                    "signal_name": "forensic_anomaly_detected",
                    "direction": "increases_risk",
                    "magnitude": 1.0,
                    "explanation": (
                        f"Forensic analysis indicates {prob:.0%} probability of digital manipulation."
                    ),
                    "source_module": "forensics",
                })
            elif prob >= 0.4:
                signals.append({
                    "signal_name": "forensic_anomaly",
                    "direction": "increases_risk",
                    "magnitude": 0.7,
                    "explanation": (
                        f"Forensic analysis indicates {prob:.0%} probability of digital manipulation. "
                        "Minor anomalies detected."
                    ),
                    "source_module": "forensics",
                })

    # ── OCR Signals ────────────────────────────────────────────────
    if ocr_result and not ocr_result.is_stub:
        low_conf_fields = [
            field for field, conf in (ocr_result.field_confidence or {}).items()
            if conf < 0.60
        ]
        if low_conf_fields:
            signals.append({
                "signal_name": "mandatory_field_missing",
                "direction": "increases_risk",
                "magnitude": 0.7,
                "explanation": (
                    f"OCR confidence is low for: {', '.join(low_conf_fields)}. "
                    "These fields may be unreadable."
                ),
                "source_module": "ocr",
            })

    # ── Document Validation (teammate's engine) ────────────────────
    # Run date/field validation using OCR-extracted data
    if ocr_result and not ocr_result.is_stub and ocr_result.structured_fields:
        try:
            from ai.risk_engine.schemas.validation import DocumentValidationInput
            from ai.risk_engine.services.validation.validator import DocumentValidationEngine

            fields = ocr_result.structured_fields
            val_input = DocumentValidationInput(
                document_id=str(ocr_result.document_id),
                case_id=str(case_id),
                doc_type="passport",
                doc_number=fields.get("doc_number"),
                expiry_date=fields.get("expiry"),
                dob=fields.get("dob"),
                issuing_country=fields.get("issuing_state"),
                structured_fields=fields,
            )

            validator = DocumentValidationEngine()
            val_result = validator.validate(val_input)

            # Convert failed validation checks to risk signals
            for check in val_result.checks:
                if not check.passed:
                    if check.rule == "expiry_not_past":
                        sig_name = "document_expired"
                    elif check.rule == "dob_sanity":
                        sig_name = "dob_in_future" if "future" in check.explanation else "dob_mismatch"
                    elif check.rule == "mandatory_fields_present":
                        sig_name = "mandatory_field_missing"
                    elif check.rule == "doc_number_format":
                        sig_name = "doc_number_format_mismatch"
                    else:
                        sig_name = f"validation_{check.rule}_failed"

                    signals.append({
                        "signal_name": sig_name,
                        "direction": "increases_risk",
                        "magnitude": 1.0,
                        "explanation": check.explanation,
                        "source_module": "validation",
                    })
        except Exception as e:
            # If validation engine fails, don't crash the whole assessment
            print(f"[VERIFAI] Document validation skipped: {e}")

    # ── No signals at all ─────────────────────────────────────────
    if not signals:
        signals.append({
            "signal_name": "no_analysis_complete",
            "direction": "neutral",
            "magnitude": 0.0,
            "explanation": "No AI modules have produced results yet. Run OCR, MRZ, face, and forensics first.",
            "source_module": "mrz",
        })

    return signals


def _compute_final_score(signals):
    """
    Use the teammate's RiskEngine to compute the weighted score.
    Falls back to simple summation if the engine isn't available.
    """
    try:
        from ai.risk_engine.services.risk_engine.engine import RiskEngine
        from ai.risk_engine.schemas.risk import RiskSignal as RESignal, SignalDirection, SourceModule

        engine = RiskEngine()

        # Convert our signal dicts to the teammate's RiskSignal objects
        re_signals = []
        for s in signals:
            direction_map = {
                "increases_risk": SignalDirection.INCREASES_RISK,
                "decreases_risk": SignalDirection.DECREASES_RISK,
                "neutral": SignalDirection.NEUTRAL,
            }
            source_map = {
                "ocr": SourceModule.OCR,
                "mrz": SourceModule.MRZ,
                "face": SourceModule.FACE,
                "forensics": SourceModule.FORENSICS,
                "validation": SourceModule.VALIDATION,
                "consistency": SourceModule.CONSISTENCY,
            }
            # Magnitude needs to be normalized to 0-1 for the RiskEngine
            raw_mag = s["magnitude"]
            normalized_mag = min(raw_mag / 100.0, 1.0) if raw_mag > 1.0 else raw_mag

            re_signals.append(RESignal(
                case_id="scoring",
                signal_name=s["signal_name"],
                direction=direction_map.get(s["direction"], SignalDirection.NEUTRAL),
                magnitude=normalized_mag,
                explanation=s["explanation"],
                source_module=source_map.get(s["source_module"], SourceModule.VALIDATION),
            ))

        result = engine.evaluate(case_id="scoring", signals=re_signals)
        return result.overall_score, result.risk_band.value

    except Exception as e:
        print(f"[VERIFAI] RiskEngine fallback: {e}")
        from ai.risk_engine.core.risk_config import default_risk_config
        score = 0.0
        for s in signals:
            w = abs(default_risk_config.get_weight(s["signal_name"]))
            mag = s["magnitude"] if s["magnitude"] <= 1.0 else s["magnitude"] / 100.0
            if s["direction"] == "increases_risk":
                score += mag * w
            elif s["direction"] == "decreases_risk":
                score = max(0.0, score - mag * w)

        score = round(max(0.0, min(100.0, score)), 2)
        if score >= 70:
            band = "high"
        elif score >= 30:
            band = "medium"
        else:
            band = "low"
        return score, band


@router.post(
    "/{case_id}/risk-assessment",
    response_model=RiskAssessmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Compute risk assessment",
    description=(
        "Aggregate all AI signals (OCR, MRZ, face, forensics, validation) into a single risk score. "
        "Uses the integrated Risk Engine for weighted scoring. "
        "Returns score (0-100), risk band, and contributing signals. "
        "This is the AI's RECOMMENDATION. The officer makes the final decision."
    ),
)
async def compute_risk_assessment(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> RiskAssessmentOut:
    """Compute risk assessment by aggregating all available signals."""

    # 1. Verify case exists
    case = await db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # 2. Load the latest result from each module
    from app.models.mrz_result import MrzResult
    from app.models.ocr_result import OcrResult
    from app.models.face_verification import FaceVerification
    from app.models.forensics_result import ForensicsResult

    async def latest(model):
        q = await db.execute(
            select(model)
            .where(model.case_id == case_id)
            .order_by(model.created_at.desc())
            .limit(1)
        )
        return q.scalar_one_or_none()

    mrz_result = await latest(MrzResult)
    ocr_result = await latest(OcrResult)
    face_result = await latest(FaceVerification)
    forensics_result = await latest(ForensicsResult)

    # 3. Collect all signals
    signals = _collect_signals(case_id, mrz_result, ocr_result, face_result, forensics_result)

    # 4. Compute final score using teammate's RiskEngine
    score, band = _compute_final_score(signals)

    # 5. Store RiskAssessment in database
    from app.models.risk_assessment import RiskAssessment, RiskSignal
    assessment = RiskAssessment(
        case_id=case_id,
        overall_score=score,
        risk_band=band,
    )
    db.add(assessment)
    await db.flush()

    for sig in signals:
        db.add(RiskSignal(
            assessment_id=assessment.id,
            case_id=case_id,
            **sig,
        ))

    # 6. Update the case's risk cache
    case.risk_score = score
    case.risk_band = band
    case.status = "reviewed"

    # 7. Audit log
    db.add(AuditLog(
        user_id=PLACEHOLDER_OFFICER_ID,
        case_id=case_id,
        action="risk_assessed",
        details=f"Score: {score:.1f}, Band: {band}, Signals: {len(signals)}",
    ))

    await db.commit()
    await db.refresh(assessment)

    # Reload with signals
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(RiskAssessment)
        .where(RiskAssessment.id == assessment.id)
        .options(selectinload(RiskAssessment.signals))
    )
    assessment = result.scalar_one()

    return RiskAssessmentOut.model_validate(assessment)
