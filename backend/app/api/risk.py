"""
VERIFAI — Risk Assessment Engine
===================================

POST /api/v1/cases/{case_id}/risk-assessment

This is the BRAIN of VERIFAI. It:
1. Collects all signals from all AI modules (OCR, MRZ, face, forensics)
2. Scores each signal (adds or subtracts risk points)
3. Computes a total risk score (0-100)
4. Assigns a risk band (low / medium / high)
5. Stores the full assessment for the officer to review

HOW RISK SCORING WORKS (non-technical):
- Every AI module produces "signals"
- Each signal says: "this INCREASES risk by X points" or "DECREASES risk by Y points"
- We add them all up
- 0-39 = LOW risk   (proceed with caution)
- 40-69 = MEDIUM risk (enhanced scrutiny)
- 70-100 = HIGH risk  (strong suspicion, recommend escalation)

This is the AI's RECOMMENDATION ONLY. The officer makes the final call.

HARDCODED SCORING TABLE:
We don't use ML here — we use explicit, explainable rules that a judge can read.
This is intentional: "the algorithm gives 30 points for a failed MRZ checksum
because ICAO 9303 states that checksum failure indicates data alteration."
"""

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


# ── Scoring Rules ──────────────────────────────────────────────────
# Each rule is: (condition_description, score_delta, explanation_for_officer)
# Positive delta = increases risk, negative = decreases risk.
# These are intentionally simple so a judge can read and understand them.

def _compute_risk(
    mrz_result,
    ocr_result,
    face_result,
    forensics_result,
) -> tuple[float, str, list[dict]]:
    """
    Core risk computation logic.

    Returns (score, band, signals_list).
    score is 0-100.
    band is 'low', 'medium', or 'high'.
    signals_list is the list of individual signal contributions.
    """
    score = 0.0
    signals = []

    # ── MRZ Signals ────────────────────────────────────────────────
    if mrz_result and not mrz_result.is_stub:
        if not mrz_result.mrz_present:
            signals.append({
                "signal_name": "MRZ_NOT_FOUND",
                "direction": "increases_risk",
                "magnitude": 25.0,
                "explanation": "No Machine-Readable Zone (MRZ) detected. Expected for a passport.",
                "source_module": "mrz",
            })
            score += 25.0
        elif mrz_result.checksum_valid is False:
            signals.append({
                "signal_name": "MRZ_CHECKSUM_FAILURE",
                "direction": "increases_risk",
                "magnitude": 40.0,
                "explanation": (
                    "MRZ checksum validation failed. Per ICAO 9303, this indicates "
                    "the document data may have been altered."
                ),
                "source_module": "mrz",
            })
            score += 40.0
        elif mrz_result.checksum_valid is True:
            signals.append({
                "signal_name": "MRZ_CHECKSUM_PASS",
                "direction": "decreases_risk",
                "magnitude": 10.0,
                "explanation": "All MRZ checksums validated. Document data is internally consistent.",
                "source_module": "mrz",
            })
            score = max(0.0, score - 10.0)

    # ── Face Verification Signals ──────────────────────────────────
    if face_result:
        if face_result.band == "mismatch":
            signals.append({
                "signal_name": "FACE_MISMATCH",
                "direction": "increases_risk",
                "magnitude": 45.0,
                "explanation": (
                    f"Face similarity score {face_result.similarity_score:.2f} — below mismatch threshold (0.50). "
                    "The person's face does not match the document photo."
                ),
                "source_module": "face",
            })
            score += 45.0
        elif face_result.band == "uncertain":
            signals.append({
                "signal_name": "FACE_UNCERTAIN",
                "direction": "increases_risk",
                "magnitude": 20.0,
                "explanation": (
                    f"Face similarity score {face_result.similarity_score:.2f} — uncertain zone (0.50-0.60). "
                    "Officer should manually compare faces."
                ),
                "source_module": "face",
            })
            score += 20.0
        elif face_result.band == "match":
            signals.append({
                "signal_name": "FACE_MATCH",
                "direction": "decreases_risk",
                "magnitude": 10.0,
                "explanation": (
                    f"Face similarity score {face_result.similarity_score:.2f} — match (>=0.60). "
                    "Person's face matches the document photo."
                ),
                "source_module": "face",
            })
            score = max(0.0, score - 10.0)
        elif face_result.band == "error":
            signals.append({
                "signal_name": "FACE_DETECTION_FAILED",
                "direction": "increases_risk",
                "magnitude": 15.0,
                "explanation": "Face could not be detected in one of the images. Re-capture recommended.",
                "source_module": "face",
            })
            score += 15.0

    # ── Forensics Signals ──────────────────────────────────────────
    if forensics_result and not forensics_result.is_stub:
        prob = forensics_result.overall_manipulation_probability
        if prob is not None:
            if prob >= 0.7:
                signals.append({
                    "signal_name": "HIGH_MANIPULATION_PROBABILITY",
                    "direction": "increases_risk",
                    "magnitude": 35.0,
                    "explanation": (
                        f"Forensic analysis indicates {prob:.0%} probability of digital manipulation. "
                        "Suspicious regions detected in the document image."
                    ),
                    "source_module": "forensics",
                })
                score += 35.0
            elif prob >= 0.4:
                signals.append({
                    "signal_name": "MODERATE_MANIPULATION_PROBABILITY",
                    "direction": "increases_risk",
                    "magnitude": 15.0,
                    "explanation": (
                        f"Forensic analysis indicates {prob:.0%} probability of digital manipulation. "
                        "Minor anomalies detected."
                    ),
                    "source_module": "forensics",
                })
                score += 15.0

    # ── OCR Signals ────────────────────────────────────────────────
    if ocr_result and not ocr_result.is_stub:
        low_conf_fields = [
            field for field, conf in ocr_result.field_confidence.items()
            if conf < 0.60
        ]
        if low_conf_fields:
            signals.append({
                "signal_name": "OCR_LOW_CONFIDENCE",
                "direction": "increases_risk",
                "magnitude": 10.0,
                "explanation": (
                    f"OCR confidence is low for: {', '.join(low_conf_fields)}. "
                    "These fields may be unreadable or illegible."
                ),
                "source_module": "ocr",
            })
            score += 10.0

    # ── No signals at all ─────────────────────────────────────────
    if not signals:
        signals.append({
            "signal_name": "NO_ANALYSIS_COMPLETE",
            "direction": "neutral",
            "magnitude": 0.0,
            "explanation": "No AI modules have produced results yet. Run OCR, MRZ, face, and forensics first.",
            "source_module": "mrz",
        })

    # ── Clamp score to 0-100 ──────────────────────────────────────
    score = max(0.0, min(100.0, score))

    # ── Band assignment ───────────────────────────────────────────
    if score >= 70:
        band = "high"
    elif score >= 40:
        band = "medium"
    else:
        band = "low"

    return score, band, signals


@router.post(
    "/{case_id}/risk-assessment",
    response_model=RiskAssessmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Compute risk assessment",
    description=(
        "Aggregate all AI signals (OCR, MRZ, face, forensics) into a single risk score. "
        "Returns a score (0-100), a risk band (low/medium/high), and the contributing signals. "
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

    # 2. Load the latest result from each module (if available)
    from app.models.mrz_result import MrzResult
    from app.models.ocr_result import OcrResult
    from app.models.face_verification import FaceVerification
    from app.models.forensics_result import ForensicsResult

    # Latest MRZ result for any document in this case
    mrz_q = await db.execute(
        select(MrzResult)
        .where(MrzResult.case_id == case_id)
        .order_by(MrzResult.created_at.desc())
        .limit(1)
    )
    mrz_result = mrz_q.scalar_one_or_none()

    # Latest OCR result
    ocr_q = await db.execute(
        select(OcrResult)
        .where(OcrResult.case_id == case_id)
        .order_by(OcrResult.created_at.desc())
        .limit(1)
    )
    ocr_result = ocr_q.scalar_one_or_none()

    # Latest face verification
    face_q = await db.execute(
        select(FaceVerification)
        .where(FaceVerification.case_id == case_id)
        .order_by(FaceVerification.created_at.desc())
        .limit(1)
    )
    face_result = face_q.scalar_one_or_none()

    # Latest forensics result
    forensics_q = await db.execute(
        select(ForensicsResult)
        .where(ForensicsResult.case_id == case_id)
        .order_by(ForensicsResult.created_at.desc())
        .limit(1)
    )
    forensics_result = forensics_q.scalar_one_or_none()

    # 3. Compute risk score
    score, band, signals = _compute_risk(mrz_result, ocr_result, face_result, forensics_result)

    # 4. Store RiskAssessment
    from app.models.risk_assessment import RiskAssessment, RiskSignal
    assessment = RiskAssessment(
        case_id=case_id,
        overall_score=score,
        risk_band=band,
    )
    db.add(assessment)
    await db.flush()  # Get assessment.id before adding signals

    for sig in signals:
        db.add(RiskSignal(
            assessment_id=assessment.id,
            case_id=case_id,
            **sig,
        ))

    # 5. Update the case's risk cache
    case.risk_score = score
    case.risk_band = band
    case.status = "reviewed"

    # 6. Audit log
    db.add(AuditLog(
        user_id=PLACEHOLDER_OFFICER_ID,
        case_id=case_id,
        action="risk_assessed",
        details=f"Score: {score:.1f}, Band: {band}, Signals: {len(signals)}",
    ))

    await db.commit()
    await db.refresh(assessment)

    # Reload signals
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(RiskAssessment)
        .where(RiskAssessment.id == assessment.id)
        .options(selectinload(RiskAssessment.signals))
    )
    assessment = result.scalar_one()

    return RiskAssessmentOut.model_validate(assessment)

