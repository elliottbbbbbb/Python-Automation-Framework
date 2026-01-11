"""
License validation service.
Handles license activation, validation, and caching.
"""

import logging
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import requests

from osrsbot.services.hardware_fingerprint import get_machine_fingerprint
from osrsbot.exceptions.license_exceptions import (
    LicenseExpiredException,
    LicenseInvalidException,
    MachineMismatchException,
    LicenseActivationException,
)

logger = logging.getLogger(__name__)


class LicenseService:
    """License validation and management service."""

    def __init__(self, api_url: str, cache_file: str = ".license_cache"):
        """
        Initialize the license service.

        Args:
            api_url: Base URL of the license API server
            cache_file: Path to cache file for storing license info
        """
        self.api_url = api_url.rstrip('/')
        self.cache_file = Path(cache_file)
        self.fingerprint = get_machine_fingerprint()
        self._cached_license: Optional[dict] = None

    def activate(self, license_key: str, client_version: str = "1.0.0") -> dict:
        """
        Activate a license key for this machine.

        Args:
            license_key: License key to activate
            client_version: Version of the client application

        Returns:
            Activation response with expiry info

        Raises:
            LicenseActivationException: If activation fails
            LicenseInvalidException: If license key is invalid
        """
        try:
            response = requests.post(
                f"{self.api_url}/api/v1/activate",
                json={
                    "license_key": license_key,
                    "machine_fingerprint": self.fingerprint,
                    "client_version": client_version
                },
                timeout=10
            )

            # Handle specific error codes
            if response.status_code == 404:
                raise LicenseInvalidException("License key not found")
            elif response.status_code == 403:
                raise LicenseInvalidException("License has been revoked")
            elif response.status_code == 409:
                raise LicenseActivationException("License already activated on different machine")
            elif response.status_code == 429:
                raise LicenseActivationException("Too many requests. Please try again later.")

            response.raise_for_status()
            data = response.json()

            if data.get("success"):
                # Cache the license info
                self._save_cache(license_key, data)
                logger.info(f"License activated successfully, expires: {data.get('expires_at')}")
                return data
            else:
                error_msg = data.get("message", "Activation failed")
                raise LicenseActivationException(error_msg)

        except requests.RequestException as e:
            logger.error(f"License activation network error: {e}")
            raise LicenseActivationException(f"Network error: {e}")

    def validate(self) -> bool:
        """
        Validate the current license.

        Returns:
            True if license is valid

        Raises:
            LicenseExpiredException: If license has expired
            LicenseInvalidException: If license is invalid or not found
            MachineMismatchException: If fingerprint doesn't match
        """
        # Try to load from cache first
        cached = self._load_cache()
        if not cached:
            raise LicenseInvalidException("No license found. Please activate a license key.")

        license_key = cached.get("license_key")

        try:
            response = requests.post(
                f"{self.api_url}/api/v1/validate",
                json={
                    "license_key": license_key,
                    "machine_fingerprint": self.fingerprint
                },
                timeout=10
            )

            # Handle rate limiting
            if response.status_code == 429:
                raise LicenseInvalidException("Too many validation requests. Please try again later.")

            response.raise_for_status()
            data = response.json()

            if not data.get("valid"):
                error = data.get("error")
                message = data.get("message", "License validation failed")

                if error == "LICENSE_EXPIRED":
                    raise LicenseExpiredException(message)
                elif error == "MACHINE_MISMATCH":
                    raise MachineMismatchException(message)
                else:
                    raise LicenseInvalidException(message)

            # Update cache with latest info
            self._save_cache(license_key, data)

            hours_remaining = data.get("hours_remaining", 0)
            logger.info(f"License valid - {hours_remaining:.1f} hours remaining")

            return True

        except requests.RequestException as e:
            logger.error(f"License validation network error: {e}")
            # Check if we have a recent cached validation (offline grace period)
            if cached and self._is_cache_recent(cached):
                logger.warning("Using cached license validation (offline mode)")
                return True
            raise LicenseInvalidException(f"Network error: {e}")

    def get_cached_info(self) -> Optional[dict]:
        """
        Get cached license information.

        Returns:
            Cached license data or None if no cache exists
        """
        return self._load_cache()

    def clear_cache(self) -> None:
        """Clear the license cache file."""
        if self.cache_file.exists():
            try:
                self.cache_file.unlink()
                logger.info("License cache cleared")
            except Exception as e:
                logger.error(f"Failed to clear license cache: {e}")

    def _save_cache(self, license_key: str, data: dict) -> None:
        """
        Save license info to cache file.

        Args:
            license_key: The license key
            data: Validation/activation response data
        """
        cache_data = {
            "license_key": license_key,
            "expires_at": data.get("expires_at"),
            "hours_remaining": data.get("hours_remaining"),
            "cached_at": datetime.utcnow().isoformat(),
            "fingerprint": self.fingerprint
        }

        try:
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            logger.debug("License cache saved")
        except Exception as e:
            logger.warning(f"Failed to save license cache: {e}")

    def _load_cache(self) -> Optional[dict]:
        """
        Load license info from cache file.

        Returns:
            Cached license data or None if cache doesn't exist or is invalid
        """
        if not self.cache_file.exists():
            return None

        try:
            with open(self.cache_file, 'r') as f:
                data = json.load(f)

            # Verify fingerprint matches (prevent cache tampering)
            if data.get("fingerprint") != self.fingerprint:
                logger.warning("License cache fingerprint mismatch - clearing cache")
                self.clear_cache()
                return None

            return data

        except Exception as e:
            logger.warning(f"Failed to load license cache: {e}")
            return None

    def _is_cache_recent(self, cache_data: dict, max_age_hours: int = 24) -> bool:
        """
        Check if cache is recent enough for offline grace period.

        Args:
            cache_data: Cached license data
            max_age_hours: Maximum age of cache in hours

        Returns:
            True if cache is recent enough
        """
        try:
            cached_at = datetime.fromisoformat(cache_data.get("cached_at"))
            age = datetime.utcnow() - cached_at
            return age < timedelta(hours=max_age_hours)
        except Exception:
            return False

    def get_license_status(self) -> dict:
        """
        Get current license status without validation.

        Returns:
            Dictionary with license status information
        """
        cached = self._load_cache()

        if not cached:
            return {
                "status": "no_license",
                "message": "No license found"
            }

        try:
            expires_at = datetime.fromisoformat(cached.get("expires_at"))
            now = datetime.utcnow()

            if now > expires_at:
                return {
                    "status": "expired",
                    "message": "License has expired",
                    "expires_at": cached.get("expires_at")
                }

            hours_remaining = (expires_at - now).total_seconds() / 3600

            return {
                "status": "active",
                "message": "License is active",
                "expires_at": cached.get("expires_at"),
                "hours_remaining": round(hours_remaining, 2)
            }

        except Exception as e:
            logger.error(f"Error checking license status: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
