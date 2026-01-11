"""Custom exceptions for OSRS Bot."""

from .license_exceptions import (
    LicenseException,
    LicenseInvalidException,
    LicenseExpiredException,
    MachineMismatchException,
    LicenseActivationException,
)

__all__ = [
    "LicenseException",
    "LicenseInvalidException",
    "LicenseExpiredException",
    "MachineMismatchException",
    "LicenseActivationException",
]
