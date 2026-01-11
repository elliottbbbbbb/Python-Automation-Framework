"""License activation endpoint."""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import License
from app.schemas import ActivateRequest, ActivateResponse
from app.auth import limiter
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/activate", response_model=ActivateResponse)
@limiter.limit("10/minute")
async def activate_license(request: ActivateRequest, db: Session = Depends(get_db)):
    """
    Activate a license key for a specific machine.

    Args:
        request: Activation request with license key and machine fingerprint
        db: Database session

    Returns:
        Activation response with expiry information

    Raises:
        HTTPException: If activation fails
    """
    # Find license by key
    license = db.query(License).filter(License.license_key == request.license_key).first()

    if not license:
        logger.warning(f"License not found: {request.license_key}")
        raise HTTPException(status_code=404, detail="License key not found")

    # Check if license is active
    if not license.is_active:
        logger.warning(f"License revoked: {request.license_key}")
        raise HTTPException(status_code=403, detail="License has been revoked")

    # Check if already activated
    if license.machine_fingerprint:
        if license.machine_fingerprint != request.machine_fingerprint:
            logger.warning(f"License already activated on different machine: {request.license_key}")
            raise HTTPException(
                status_code=409,
                detail="License key already activated on different machine"
            )

        # Already activated on this machine - return current expiry
        if license.expires_at and datetime.utcnow() < license.expires_at:
            logger.info(f"License already active: {request.license_key}")
            return ActivateResponse(
                success=True,
                expires_at=license.expires_at.isoformat(),
                duration_hours=license.duration_hours,
                message="License already activated for this machine"
            )

    # Activate license
    license.machine_fingerprint = request.machine_fingerprint
    license.expires_at = datetime.utcnow() + timedelta(hours=license.duration_hours)
    license.activation_count += 1
    license.last_validated_at = datetime.utcnow()

    # Store client version in custom_metadata if not exists
    metadata = license.custom_metadata if license.custom_metadata else {}
    metadata["client_version"] = request.client_version
    metadata["activated_at"] = datetime.utcnow().isoformat()
    license.custom_metadata = metadata

    db.commit()
    db.refresh(license)

    logger.info(f"License activated: {request.license_key}, expires: {license.expires_at}")

    return ActivateResponse(
        success=True,
        expires_at=license.expires_at.isoformat(),
        duration_hours=license.duration_hours,
        message="License activated successfully"
    )
