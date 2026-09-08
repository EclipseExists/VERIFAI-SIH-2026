"""Document Validation Schemas.

Adapted from teammate's code. Self-contained.
"""

from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class ValidationCheck(BaseModel):
    """Result of an individual deterministic document validation rule."""
    rule: str = Field(..., description="Rule identifier.")
    passed: bool = Field(..., description="Whether the check passed.")
    explanation: str = Field(..., description="Human-readable explanation.")
    severity: str = Field(default="critical", description="Severity level.")


class DocumentValidationInput(BaseModel):
    """Input payload for the Document Validation Engine."""
    document_id: Union[UUID, str] = Field(...)
    case_id: Union[UUID, str] = Field(...)
    doc_type: str = Field(default="passport")
    issuing_country: Optional[str] = Field(default=None)
    doc_number: Optional[str] = Field(default=None)
    expiry_date: Optional[str] = Field(default=None)
    issue_date: Optional[str] = Field(default=None)
    dob: Optional[str] = Field(default=None)
    structured_fields: Dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    """Aggregated output of deterministic document validation."""
    document_id: Union[UUID, str] = Field(...)
    case_id: Optional[Union[UUID, str]] = Field(default=None)
    is_valid: bool = Field(...)
    checks: List[ValidationCheck] = Field(default_factory=list)
