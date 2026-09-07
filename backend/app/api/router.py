"""
VERIFAI — Main API Router
============================

All API routes assembled in one place.
"""

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.cases import router as cases_router
from app.api.documents import router as documents_router
from app.api.face_verification import router as face_router
from app.api.ocr import router as ocr_router
from app.api.mrz import router as mrz_router
from app.api.forensics import router as forensics_router
from app.api.risk import router as risk_router
from app.api.auth import router as auth_router
from app.api.case_full import router as case_full_router

api_router = APIRouter()

# Health check
api_router.include_router(health_router, prefix="/health", tags=["health"])

# Auth — login, register
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])

# Case management — create, list, get, decision
api_router.include_router(cases_router, prefix="/cases", tags=["cases"])

# Full case results — GET /cases/{id}/full (everything in one call)
api_router.include_router(case_full_router, prefix="/cases", tags=["cases"])

# Document upload — POST /cases/{id}/documents
api_router.include_router(documents_router, prefix="/cases", tags=["documents"])

# Face verification — POST /cases/{id}/face-verification
api_router.include_router(face_router, prefix="/cases", tags=["face-verification"])

# Risk assessment — POST /cases/{id}/risk-assessment
api_router.include_router(risk_router, prefix="/cases", tags=["risk"])

# Document-level AI modules — /documents/{id}/ocr|mrz|forensics
api_router.include_router(ocr_router, prefix="/documents", tags=["ocr"])
api_router.include_router(mrz_router, prefix="/documents", tags=["mrz"])
api_router.include_router(forensics_router, prefix="/documents", tags=["forensics"])
