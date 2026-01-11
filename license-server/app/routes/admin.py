"""Admin endpoints for license management."""

from fastapi import APIRouter, Depends, HTTPException, Security
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import License
from app.schemas import LicenseInfo
from app.auth import get_api_key
import secrets
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/admin/licenses", response_model=LicenseInfo)
async def create_license(
    duration_hours: int,
    notes: str = None,
    db: Session = Depends(get_db),
    api_key: str = Security(get_api_key)
):
    """
    Create a new license key (admin only).

    Args:
        duration_hours: License duration in hours
        notes: Optional notes (email, customer ID, etc.)
        db: Database session
        api_key: Admin API key

    Returns:
        Created license information
    """
    # Generate unique license key
    license_key = generate_license_key()

    # Create license
    license = License(
        license_key=license_key,
        duration_hours=duration_hours,
        custom_metadata={"notes": notes} if notes else None
    )

    db.add(license)
    db.commit()
    db.refresh(license)

    logger.info(f"License created: {license_key}, duration: {duration_hours}h")

    return LicenseInfo.from_orm(license)


@router.get("/admin/licenses", response_model=List[LicenseInfo])
async def list_licenses(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    api_key: str = Security(get_api_key)
):
    """
    List all licenses (admin only).

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        api_key: Admin API key

    Returns:
        List of licenses
    """
    licenses = db.query(License).offset(skip).limit(limit).all()
    return [LicenseInfo.from_orm(lic) for lic in licenses]


@router.get("/admin/licenses/{license_key}", response_model=LicenseInfo)
async def get_license(
    license_key: str,
    db: Session = Depends(get_db),
    api_key: str = Security(get_api_key)
):
    """
    Get license details (admin only).

    Args:
        license_key: License key to retrieve
        db: Database session
        api_key: Admin API key

    Returns:
        License information

    Raises:
        HTTPException: If license not found
    """
    license = db.query(License).filter(License.license_key == license_key).first()

    if not license:
        raise HTTPException(status_code=404, detail="License not found")

    return LicenseInfo.from_orm(license)


@router.delete("/admin/licenses/{license_key}")
async def revoke_license(
    license_key: str,
    db: Session = Depends(get_db),
    api_key: str = Security(get_api_key)
):
    """
    Revoke a license (admin only).

    Args:
        license_key: License key to revoke
        db: Database session
        api_key: Admin API key

    Returns:
        Success message

    Raises:
        HTTPException: If license not found
    """
    license = db.query(License).filter(License.license_key == license_key).first()

    if not license:
        raise HTTPException(status_code=404, detail="License not found")

    license.is_active = False
    db.commit()

    logger.info(f"License revoked: {license_key}")

    return {"message": "License revoked successfully"}


def generate_license_key() -> str:
    """
    Generate a random license key in format: XXXX-XXXX-XXXX-XXXX

    Returns:
        Random license key
    """
    parts = []
    for _ in range(4):
        part = secrets.token_hex(2).upper()
        parts.append(part)
    return "-".join(parts)
