"""License-related exceptions."""


class LicenseException(Exception):
    """Base exception for license errors."""
    pass


class LicenseInvalidException(LicenseException):
    """Raised when license key is invalid or not found."""
    pass


class LicenseExpiredException(LicenseException):
    """Raised when license has expired."""
    pass


class MachineMismatchException(LicenseException):
    """Raised when license is tied to different machine."""
    pass


class LicenseActivationException(LicenseException):
    """Raised when license activation fails."""
    pass
