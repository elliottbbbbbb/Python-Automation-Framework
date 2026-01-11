"""Authentication and rate limiting middleware."""

import os
from fastapi import HTTPException, Security, Request
from fastapi.security.api_key import APIKeyHeader
from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# API key authentication
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def get_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Validate API key for admin endpoints.

    Args:
        api_key: API key from header

    Returns:
        API key if valid

    Raises:
        HTTPException: If API key is invalid
    """
    expected_key = os.getenv("API_KEY")

    if not expected_key:
        # In development, allow without API key
        if os.getenv("ENVIRONMENT") == "development":
            return "development"
        raise HTTPException(status_code=500, detail="API key not configured")

    if api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return api_key
