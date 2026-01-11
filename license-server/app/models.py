"""Database models for license management."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from app.database import Base


class License(Base):
    """License model for storing license information."""

    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, index=True)
    license_key = Column(String(64), unique=True, nullable=False, index=True)
    duration_hours = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    expires_at = Column(DateTime, nullable=True)
    machine_fingerprint = Column(String(64), index=True, nullable=True)
    activation_count = Column(Integer, default=0)
    last_validated_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    custom_metadata = Column(JSON, nullable=True)  # Store additional info (email, purchase_id, etc.)

    def __repr__(self):
        return f"<License {self.license_key}>"

    def to_dict(self):
        """Convert license to dictionary."""
        return {
            "id": self.id,
            "license_key": self.license_key,
            "duration_hours": self.duration_hours,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "activation_count": self.activation_count,
            "is_active": self.is_active,
            "last_validated_at": self.last_validated_at.isoformat() if self.last_validated_at else None,
        }

    def is_expired(self) -> bool:
        """Check if license has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def get_hours_remaining(self) -> float:
        """Get hours remaining until expiration."""
        if not self.expires_at:
            return 0
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.total_seconds() / 3600)
