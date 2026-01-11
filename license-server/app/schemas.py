"""Pydantic schemas for request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ActivateRequest(BaseModel):
    """Request schema for license activation."""

    license_key: str = Field(..., min_length=4, max_length=64, description="License key to activate")
    machine_fingerprint: str = Field(..., min_length=64, max_length=64, description="SHA256 machine fingerprint")
    client_version: str = Field(default="1.0.0", description="Client version")


class ActivateResponse(BaseModel):
    """Response schema for license activation."""

    success: bool
    expires_at: Optional[str] = None
    duration_hours: Optional[int] = None
    message: str


class ValidateRequest(BaseModel):
    """Request schema for license validation."""

    license_key: str = Field(..., min_length=4, max_length=64, description="License key to validate")
    machine_fingerprint: str = Field(..., min_length=64, max_length=64, description="SHA256 machine fingerprint")


class ValidateResponse(BaseModel):
    """Response schema for license validation."""

    valid: bool
    expires_at: Optional[str] = None
    hours_remaining: Optional[float] = None
    message: str
    error: Optional[str] = None


class LicenseInfo(BaseModel):
    """License information schema."""

    id: int
    license_key: str
    duration_hours: int
    created_at: datetime
    expires_at: Optional[datetime]
    activation_count: int
    is_active: bool
    last_validated_at: Optional[datetime]

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
