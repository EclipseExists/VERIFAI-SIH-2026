"""
VERIFAI — Health Check Schema
"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response from the health check endpoint."""
    status: str
    version: str
    database: str

