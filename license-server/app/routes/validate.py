"""License validation endpoint."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import License
from app.schemas import ValidateRequest, ValidateResponse
from app.auth import limiter
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/validate", response_model=ValidateResponse)
@limiter.limit("30/minute")
async def validate_license(validate_request: ValidateRequest, request: Request, db: Session = Depends(get_db)):
    """
    Validate a license key for a specific machine.

    Args:
        request: Validation request with license key and machine fingerprint
        db: Database session

    Returns:
        Validation response with license status

    Raises:
        HTTPException: If validation request is malformed
    """
    # Find license by key
    license = db.query(License).filter(License.license_key == validate_request.license_key).first()

    if not license:
        logger.warning(f"License not found: {validate_request.license_key}")
        return ValidateResponse(
            valid=False,
            error="LICENSE_NOT_FOUND",
            message="License key not found"
        )

    # Check if machine fingerprint matches
    if license.machine_fingerprint != validate_request.machine_fingerprint:
        logger.warning(f"Machine mismatch for license: {validate_request.license_key}")
        return ValidateResponse(
            valid=False,
            error="MACHINE_MISMATCH",
            message="License is registered to a different machine"
        )

    # Check if license is active
    if not license.is_active:
        logger.warning(f"License revoked: {validate_request.license_key}")
        return ValidateResponse(
            valid=False,
            error="LICENSE_REVOKED",
            message="License has been revoked"
        )

    # Check if license has expired
    if license.is_expired():
        logger.warning(f"License expired: {validate_request.license_key}")
        return ValidateResponse(
            valid=False,
            error="LICENSE_EXPIRED",
            message="License has expired",
            expires_at=license.expires_at.isoformat() if license.expires_at else None
        )

    # Update last validation timestamp
    license.last_validated_at = datetime.utcnow()
    db.commit()

    hours_remaining = license.get_hours_remaining()

    logger.info(f"License valid: {validate_request.license_key}, {hours_remaining:.2f}h remaining")

    return ValidateResponse(
        valid=True,
        expires_at=license.expires_at.isoformat() if license.expires_at else None,
        hours_remaining=round(hours_remaining, 2),
        message="License valid"
    )
