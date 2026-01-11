# License System Implementation Plan

## Executive Summary

Implement a comprehensive license validation system for the OSRS Bot Framework with:
- **Hardware-locked licenses** tied to specific machines
- **In-app GUI activation** prompt on first launch
- **Immediate shutdown** on validation failure
- **Time-based licenses** (1hr, 24hr, 7 days, custom durations)
- **Backend API** for license validation and management

---

## User Requirements

Based on clarification questions:
1. **API Backend:** Need recommendations for hosting solution
2. **Key Distribution:** In-app GUI prompt for license key entry
3. **Failure Behavior:** Immediate shutdown with clear error message
4. **Usage Tracking:** Hardware fingerprinting to prevent key sharing

---

## Recommended Architecture

### Backend API Solution

**Recommendation: Use Gumroad or LemonSqueezy + Custom Validation Server**

**Why this hybrid approach:**
1. **Payment Processing:** Gumroad/LemonSqueezy handles payments, checkout, receipts
2. **License Generation:** Auto-generate unique keys on purchase
3. **Validation Server:** Your lightweight API validates keys + enforces hardware locks
4. **Cost Effective:** No payment gateway integration needed, minimal hosting costs

**Alternative (Full Custom):** Build Flask/FastAPI server if you want 100% control over pricing, tiers, and data.

### Architecture Diagram

```
┌─────────────┐         ┌──────────────────┐         ┌─────────────┐
│  User Buys  │────────>│   Gumroad API    │────────>│   Webhook   │
│   License   │         │ (Payment/Keys)   │         │   Handler   │
└─────────────┘         └──────────────────┘         └──────┬──────┘
                                                             │
                                                             ▼
                        ┌────────────────────────────────────────┐
                        │      Your License Database             │
                        │  (PostgreSQL/MySQL/SQLite/Firebase)    │
                        │                                        │
                        │  - license_key (unique)                │
                        │  - duration_hours (1, 24, 168, etc.)   │
                        │  - created_at, expires_at              │
                        │  - machine_fingerprint (locked after)  │
                        │  - activation_count, last_check        │
                        └────────────┬───────────────────────────┘
                                     │
                                     ▼
                        ┌────────────────────────────┐
                        │  License Validation API    │
                        │  (Flask/FastAPI/Express)   │
                        │                            │
                        │  POST /api/activate        │
                        │  POST /api/validate        │
                        │  GET  /api/status          │
                        └────────────┬───────────────┘
                                     │
                                     ▼
                        ┌────────────────────────────┐
                        │     OSRS Bot Client        │
                        │                            │
                        │  1. GUI Prompt for Key     │
                        │  2. Generate Fingerprint   │
                        │  3. Send to API            │
                        │  4. Cache Response         │
                        │  5. Start Bot (if valid)   │
                        └────────────────────────────┘
```

---

## Implementation Components

### 1. Backend API Server

**Recommended Stack:**
- **Framework:** FastAPI (Python) - fast, async, auto-docs
- **Database:** PostgreSQL (production) or SQLite (development)
- **Hosting:** Railway.app, Render.com, or DigitalOcean ($5/mo)
- **Security:** API key authentication, rate limiting, HTTPS only

**API Endpoints:**

#### POST /api/v1/activate
**Purpose:** First-time license activation (ties key to machine)

**Request:**
```json
{
  "license_key": "XXXX-XXXX-XXXX-XXXX",
  "machine_fingerprint": "sha256_hash_of_hardware_id",
  "client_version": "1.0.0"
}
```

**Response (Success):**
```json
{
  "success": true,
  "expires_at": "2026-01-12T15:30:00Z",
  "duration_hours": 24,
  "message": "License activated successfully"
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "ALREADY_ACTIVATED",
  "message": "License key already activated on different machine"
}
```

#### POST /api/v1/validate
**Purpose:** Check if license is still valid (called on each bot startup)

**Request:**
```json
{
  "license_key": "XXXX-XXXX-XXXX-XXXX",
  "machine_fingerprint": "sha256_hash_of_hardware_id"
}
```

**Response:**
```json
{
  "valid": true,
  "expires_at": "2026-01-12T15:30:00Z",
  "hours_remaining": 23.5,
  "message": "License valid"
}
```

### 2. Client-Side Components

#### New Files to Create

**1. `src/osrsbot/services/license_service.py`**
- Main license validation logic
- Hardware fingerprinting
- API communication
- Response caching

**2. `src/osrsbot/services/hardware_fingerprint.py`**
- Generate unique machine ID from:
  - CPU info (model, cores, serial if available)
  - MAC address (primary network adapter)
  - Motherboard UUID
  - OS install ID
- SHA256 hash for privacy

**3. `src/osrsbot/ui/license_dialog.py`**
- Tkinter GUI dialog for license key entry
- Validation feedback (loading spinner, error messages)
- "Activate License" button
- Links to purchase page

**4. `src/osrsbot/models/license.py`**
- Data classes for license information
- Pydantic models for validation

**5. `src/osrsbot/exceptions/license_exceptions.py`**
- Custom exception classes:
  - `LicenseExpiredException`
  - `LicenseInvalidException`
  - `MachineMismatchException`
  - `LicenseActivationException`

---

## Detailed Implementation Plan

### Phase 1: Backend API Server

**File Structure:**
```
license-server/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── database.py          # Database connection
│   ├── auth.py              # API key middleware
│   └── routes/
│       ├── __init__.py
│       ├── activate.py      # /api/v1/activate
│       └── validate.py      # /api/v1/validate
├── requirements.txt
├── .env                     # Secrets (DB URL, API keys)
└── Dockerfile              # For deployment
```

**Database Schema:**
```sql
CREATE TABLE licenses (
    id SERIAL PRIMARY KEY,
    license_key VARCHAR(64) UNIQUE NOT NULL,
    duration_hours INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    machine_fingerprint VARCHAR(64),
    activation_count INTEGER DEFAULT 0,
    last_validated_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB  -- Store additional info (email, purchase_id, etc.)
);

CREATE INDEX idx_license_key ON licenses(license_key);
CREATE INDEX idx_fingerprint ON licenses(machine_fingerprint);
```

**Key Logic:**

```python
# Activation Flow
def activate_license(key: str, fingerprint: str) -> dict:
    license = db.query(License).filter_by(license_key=key).first()

    if not license:
        raise HTTPException(404, "License key not found")

    if not license.is_active:
        raise HTTPException(403, "License has been revoked")

    # Check if already activated
    if license.machine_fingerprint:
        if license.machine_fingerprint != fingerprint:
            raise HTTPException(409, "License already activated on different machine")

    # Activate license
    license.machine_fingerprint = fingerprint
    license.expires_at = datetime.utcnow() + timedelta(hours=license.duration_hours)
    license.activation_count += 1
    db.commit()

    return {
        "success": True,
        "expires_at": license.expires_at.isoformat(),
        "duration_hours": license.duration_hours
    }

# Validation Flow
def validate_license(key: str, fingerprint: str) -> dict:
    license = db.query(License).filter_by(license_key=key).first()

    if not license:
        return {"valid": False, "error": "LICENSE_NOT_FOUND"}

    if license.machine_fingerprint != fingerprint:
        return {"valid": False, "error": "MACHINE_MISMATCH"}

    if datetime.utcnow() > license.expires_at:
        return {"valid": False, "error": "LICENSE_EXPIRED"}

    if not license.is_active:
        return {"valid": False, "error": "LICENSE_REVOKED"}

    # Update last validation timestamp
    license.last_validated_at = datetime.utcnow()
    db.commit()

    hours_remaining = (license.expires_at - datetime.utcnow()).total_seconds() / 3600

    return {
        "valid": True,
        "expires_at": license.expires_at.isoformat(),
        "hours_remaining": round(hours_remaining, 2)
    }
```

---

### Phase 2: Client-Side Implementation

#### Step 1: Hardware Fingerprinting

**File:** `src/osrsbot/services/hardware_fingerprint.py`

```python
"""
Hardware fingerprinting for machine identification.
Generates a unique, deterministic hash for the current machine.
"""
import hashlib
import platform
import uuid
import subprocess
from typing import Optional

def get_machine_fingerprint() -> str:
    """
    Generate a unique fingerprint for this machine.

    Returns:
        SHA256 hash of hardware identifiers
    """
    components = []

    # CPU info
    components.append(platform.processor())

    # MAC address of primary network interface
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff)
                    for i in range(0, 48, 8)])
    components.append(mac)

    # Motherboard UUID (Windows)
    try:
        if platform.system() == "Windows":
            result = subprocess.check_output(
                'wmic csproduct get uuid',
                shell=True
            ).decode()
            uuid_line = result.split('\n')[1].strip()
            components.append(uuid_line)
    except:
        pass

    # Machine ID (cross-platform fallback)
    components.append(platform.node())  # hostname
    components.append(platform.machine())  # architecture

    # Create deterministic hash
    fingerprint_string = '|'.join(components)
    fingerprint_hash = hashlib.sha256(fingerprint_string.encode()).hexdigest()

    return fingerprint_hash
```

#### Step 2: License Service

**File:** `src/osrsbot/services/license_service.py`

```python
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
)

logger = logging.getLogger(__name__)

class LicenseService:
    """License validation and management service."""

    def __init__(self, api_url: str, cache_file: str = ".license_cache"):
        self.api_url = api_url
        self.cache_file = Path(cache_file)
        self.fingerprint = get_machine_fingerprint()
        self._cached_license: Optional[dict] = None

    def activate(self, license_key: str) -> dict:
        """
        Activate a license key for this machine.

        Args:
            license_key: License key to activate

        Returns:
            Activation response with expiry info

        Raises:
            LicenseActivationException: If activation fails
        """
        try:
            response = requests.post(
                f"{self.api_url}/api/v1/activate",
                json={
                    "license_key": license_key,
                    "machine_fingerprint": self.fingerprint,
                    "client_version": "1.0.0"
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if data.get("success"):
                # Cache the license info
                self._save_cache(license_key, data)
                logger.info(f"License activated successfully, expires: {data['expires_at']}")
                return data
            else:
                raise LicenseInvalidException(data.get("message", "Activation failed"))

        except requests.RequestException as e:
            logger.error(f"License activation failed: {e}")
            raise LicenseInvalidException(f"Network error: {e}")

    def validate(self) -> bool:
        """
        Validate the current license.

        Returns:
            True if license is valid

        Raises:
            LicenseExpiredException: If license has expired
            LicenseInvalidException: If license is invalid
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
            logger.error(f"License validation failed: {e}")
            raise LicenseInvalidException(f"Network error: {e}")

    def get_cached_info(self) -> Optional[dict]:
        """Get cached license information."""
        return self._load_cache()

    def _save_cache(self, license_key: str, data: dict) -> None:
        """Save license info to cache file."""
        cache_data = {
            "license_key": license_key,
            "expires_at": data.get("expires_at"),
            "hours_remaining": data.get("hours_remaining"),
            "cached_at": datetime.utcnow().isoformat()
        }

        try:
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f)
        except Exception as e:
            logger.warning(f"Failed to save license cache: {e}")

    def _load_cache(self) -> Optional[dict]:
        """Load license info from cache file."""
        if not self.cache_file.exists():
            return None

        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load license cache: {e}")
            return None
```

#### Step 3: GUI License Dialog

**File:** `src/osrsbot/ui/license_dialog.py`

```python
"""
License activation dialog GUI.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Callable, Optional

class LicenseDialog:
    """GUI dialog for license key activation."""

    def __init__(self,
                 on_activate: Callable[[str], bool],
                 purchase_url: str = "https://yoursite.com/buy"):
        self.on_activate = on_activate
        self.purchase_url = purchase_url
        self.result: Optional[bool] = None

        # Create window
        self.root = tk.Tk()
        self.root.title("License Activation")
        self.root.geometry("500x300")
        self.root.resizable(False, False)

        # Center window
        self.root.eval('tk::PlaceWindow . center')

        self._build_ui()

    def _build_ui(self):
        """Build the dialog UI."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(
            main_frame,
            text="OSRS Bot - License Activation",
            font=("Helvetica", 16, "bold")
        )
        title.pack(pady=(0, 10))

        # Description
        desc = ttk.Label(
            main_frame,
            text="Enter your license key to activate the bot.",
            font=("Helvetica", 10)
        )
        desc.pack(pady=(0, 20))

        # License key entry
        key_frame = ttk.Frame(main_frame)
        key_frame.pack(fill=tk.X, pady=10)

        ttk.Label(key_frame, text="License Key:").pack(side=tk.LEFT, padx=(0, 10))

        self.key_entry = ttk.Entry(key_frame, width=35, font=("Courier", 11))
        self.key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.key_entry.focus()

        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)

        # Activate button
        self.activate_btn = ttk.Button(
            button_frame,
            text="Activate License",
            command=self._on_activate_clicked
        )
        self.activate_btn.pack(side=tk.LEFT, padx=5)

        # Purchase link
        purchase_btn = ttk.Button(
            button_frame,
            text="Buy License",
            command=self._open_purchase_url
        )
        purchase_btn.pack(side=tk.LEFT, padx=5)

        # Status label
        self.status_label = ttk.Label(
            main_frame,
            text="",
            foreground="blue",
            font=("Helvetica", 9)
        )
        self.status_label.pack(pady=10)

        # Bind Enter key
        self.key_entry.bind('<Return>', lambda e: self._on_activate_clicked())

    def _on_activate_clicked(self):
        """Handle activate button click."""
        license_key = self.key_entry.get().strip()

        if not license_key:
            messagebox.showerror("Error", "Please enter a license key")
            return

        # Disable button and show loading
        self.activate_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Activating license...", foreground="blue")

        # Run activation in background thread
        thread = threading.Thread(
            target=self._activate_license,
            args=(license_key,)
        )
        thread.start()

    def _activate_license(self, license_key: str):
        """Activate license in background thread."""
        try:
            success = self.on_activate(license_key)

            if success:
                self.result = True
                self.root.after(0, self._on_activation_success)
            else:
                self.root.after(0, self._on_activation_failed, "Activation failed")

        except Exception as e:
            self.root.after(0, self._on_activation_failed, str(e))

    def _on_activation_success(self):
        """Handle successful activation."""
        messagebox.showinfo(
            "Success",
            "License activated successfully!\nThe bot will now start."
        )
        self.root.destroy()

    def _on_activation_failed(self, error: str):
        """Handle activation failure."""
        messagebox.showerror("Activation Failed", error)
        self.activate_btn.config(state=tk.NORMAL)
        self.status_label.config(text="", foreground="red")

    def _open_purchase_url(self):
        """Open purchase URL in browser."""
        import webbrowser
        webbrowser.open(self.purchase_url)

    def show(self) -> bool:
        """
        Show the dialog and wait for result.

        Returns:
            True if activation successful, False otherwise
        """
        self.root.mainloop()
        return self.result if self.result is not None else False
```

#### Step 4: Integration into ScriptRunner

**File:** `src/osrsbot/core/runner.py`

**Modify the `__init__` method:**

```python
def __init__(self, window_title: str, config_file: str = "config.json"):
    """Initialize the script runner with license validation."""

    # Load config first
    self.config = Config(config_file)

    # NEW: License validation before initializing anything else
    self._validate_license()

    # Continue with normal initialization
    logger.info("License validated successfully")

    self.interface = GameInterface(self.config)
    # ... rest of initialization

def _validate_license(self) -> None:
    """
    Validate license before allowing bot execution.

    Raises:
        SystemExit: If license validation fails
    """
    from osrsbot.services.license_service import LicenseService
    from osrsbot.ui.license_dialog import LicenseDialog
    from osrsbot.exceptions.license_exceptions import (
        LicenseExpiredException,
        LicenseInvalidException,
    )

    # Get API URL from config or environment
    api_url = os.getenv("LICENSE_API_URL",
                        self.config.get("license", "api_url",
                                       default="https://your-api.com"))

    license_service = LicenseService(api_url=api_url)

    try:
        # Try to validate existing license
        license_service.validate()
        logger.info("✓ License validated successfully")

    except LicenseInvalidException:
        # No license found - show activation dialog
        logger.info("No active license found. Please activate.")

        def activate_callback(key: str) -> bool:
            try:
                license_service.activate(key)
                return True
            except Exception as e:
                logger.error(f"Activation failed: {e}")
                return False

        dialog = LicenseDialog(
            on_activate=activate_callback,
            purchase_url=self.config.get("license", "purchase_url",
                                        default="https://yoursite.com/buy")
        )

        if not dialog.show():
            logger.error("License activation cancelled by user")
            print("\n❌ License activation required to use this bot.")
            print("   Visit: https://yoursite.com/buy")
            raise SystemExit(1)

    except LicenseExpiredException as e:
        logger.error(f"License expired: {e}")
        print(f"\n❌ License Expired: {e}")
        print("   Purchase a new license at: https://yoursite.com/buy")
        raise SystemExit(1)

    except Exception as e:
        logger.error(f"License validation failed: {e}")
        print(f"\n❌ License Error: {e}")
        raise SystemExit(1)
```

---

### Phase 3: Configuration and Dependencies

#### Update `pyproject.toml`

Add new dependencies:

```toml
[project]
dependencies = [
    # ... existing dependencies
    "requests>=2.31.0",      # For API calls
    "pydantic>=2.0.0",       # For data validation (if not already included)
]
```

#### Update `config.json`

Add license configuration section:

```json
{
  "license": {
    "api_url": "https://your-license-api.com",
    "purchase_url": "https://yoursite.com/buy",
    "timeout": 10,
    "cache_file": ".license_cache"
  },

  // ... rest of config
}
```

#### Update `.env.example`

Add license environment variables:

```bash
# License Configuration
LICENSE_API_URL=https://your-license-api.com
```

---

### Phase 4: Exception Handling

**File:** `src/osrsbot/exceptions/license_exceptions.py`

```python
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
```

---

## File Changes Summary

### Files to Create

1. **Backend API (Separate Repository):**
   - `license-server/app/main.py` - FastAPI application
   - `license-server/app/models.py` - Database models
   - `license-server/app/schemas.py` - Request/response schemas
   - `license-server/app/database.py` - DB connection
   - `license-server/app/routes/activate.py` - Activation endpoint
   - `license-server/app/routes/validate.py` - Validation endpoint
   - `license-server/requirements.txt` - Python dependencies
   - `license-server/.env` - Environment variables
   - `license-server/Dockerfile` - Docker deployment

2. **Client-Side (OSRS Bot Framework):**
   - `src/osrsbot/services/license_service.py` - License validation service
   - `src/osrsbot/services/hardware_fingerprint.py` - Machine fingerprinting
   - `src/osrsbot/ui/license_dialog.py` - GUI activation dialog
   - `src/osrsbot/models/license.py` - License data models
   - `src/osrsbot/exceptions/license_exceptions.py` - Custom exceptions
   - `tests/unit/services/test_license_service.py` - Unit tests
   - `tests/unit/services/test_hardware_fingerprint.py` - Fingerprint tests

### Files to Modify

1. `src/osrsbot/core/runner.py`
   - Add `_validate_license()` method in `__init__`
   - Import license services
   - Handle license exceptions

2. `pyproject.toml`
   - Add `requests` dependency

3. `config.json`
   - Add `license` configuration section

4. `.env.example`
   - Add `LICENSE_API_URL` variable

---

## Security Considerations

### Client-Side Security

1. **No Key Storage in Code:** License keys stored in encrypted cache file only
2. **Fingerprint Privacy:** Hardware fingerprint is one-way SHA256 hash
3. **HTTPS Only:** All API calls must use HTTPS
4. **Timeout Protection:** 10-second timeout on all network calls
5. **Error Messages:** Don't reveal system details in error messages

### Server-Side Security

1. **API Authentication:** Require API key for admin endpoints
2. **Rate Limiting:** Prevent brute force key guessing (10 req/min per IP)
3. **SQL Injection:** Use parameterized queries (SQLAlchemy ORM)
4. **Input Validation:** Validate all inputs with Pydantic schemas
5. **CORS:** Restrict to bot clients only
6. **Logging:** Log all activation attempts for abuse detection

### EXE Packaging Considerations

When packaging as executable with PyInstaller:

1. **Obfuscation:** Use PyArmor or similar to obfuscate Python bytecode
2. **String Encryption:** Encrypt API URLs and sensitive strings
3. **Anti-Debugging:** Add anti-debugging checks in license service
4. **Certificate Pinning:** Pin SSL certificate of license server
5. **Integrity Checks:** Verify EXE hasn't been modified

**Note:** No protection is 100% secure. Determined attackers can always crack it. Focus on making it not worth their effort.

---

## Deployment Guide

### Backend Deployment Options

#### Option 1: Railway.app (Recommended for Beginners)
- **Cost:** Free tier available, $5/mo for production
- **Setup:** Connect GitHub repo, auto-deploy on push
- **Database:** Built-in PostgreSQL
- **Scaling:** Auto-scales based on usage

**Steps:**
1. Push code to GitHub
2. Connect Railway to repo
3. Add environment variables (DB_URL, SECRET_KEY)
4. Deploy automatically

#### Option 2: DigitalOcean App Platform
- **Cost:** $5/mo for basic droplet
- **Setup:** Docker-based deployment
- **Database:** Managed PostgreSQL ($15/mo) or self-hosted
- **Control:** Full SSH access

#### Option 3: Render.com
- **Cost:** Free tier, $7/mo for production
- **Setup:** Similar to Railway
- **Database:** Built-in PostgreSQL

### Database Options

1. **Production:** PostgreSQL (Railway/DigitalOcean managed)
2. **Development:** SQLite (local file, easy testing)
3. **Scale:** Add Redis for caching validation responses

---

## Testing Strategy

### Unit Tests

**Test License Service:**
```python
def test_activate_new_license():
    """Test activating a new license key."""
    service = LicenseService(api_url="http://test.com")
    result = service.activate("TEST-KEY-1234")
    assert result["success"] == True

def test_validate_expired_license():
    """Test validation fails for expired license."""
    with pytest.raises(LicenseExpiredException):
        service.validate()

def test_machine_mismatch():
    """Test validation fails on different machine."""
    with pytest.raises(MachineMismatchException):
        service.validate()
```

**Test Hardware Fingerprint:**
```python
def test_fingerprint_deterministic():
    """Test fingerprint is consistent across calls."""
    fp1 = get_machine_fingerprint()
    fp2 = get_machine_fingerprint()
    assert fp1 == fp2

def test_fingerprint_format():
    """Test fingerprint is SHA256 hash."""
    fp = get_machine_fingerprint()
    assert len(fp) == 64
    assert all(c in '0123456789abcdef' for c in fp)
```

### Integration Tests

**Test Full Flow:**
1. Start bot without license → Show dialog
2. Enter valid key → Activate successfully
3. Restart bot → Validate from cache
4. Wait for expiry → Show expired message

### Manual Testing Checklist

- [ ] Fresh install - no license → Dialog appears
- [ ] Enter valid 1hr key → Activates successfully
- [ ] Restart bot within 1hr → Starts without prompt
- [ ] Wait 1hr → Shows expired message
- [ ] Enter invalid key → Shows clear error
- [ ] Network offline → Shows connection error
- [ ] Different machine same key → Shows "already activated" error

---

## Future Enhancements

### Phase 2 Features (Optional)

1. **Auto-Renewal:**
   - Integrate with payment processor webhooks
   - Auto-extend license on subscription payment

2. **Grace Period:**
   - Allow 24h offline usage after last successful validation
   - Cache expires_at timestamp

3. **Admin Dashboard:**
   - Web UI to view active licenses
   - Manually revoke/extend licenses
   - View usage statistics

4. **License Tiers:**
   - Basic: Limited scripts, 1hr licenses
   - Premium: All scripts, 7-day licenses
   - Enterprise: Custom duration, priority support

5. **Telemetry (Optional):**
   - Track which scripts are used most
   - Success rates for anti-ban effectiveness
   - Crash reporting

---

## Cost Estimation

### Monthly Costs

**Minimal Setup (Solo Developer):**
- Backend Hosting: $0-5 (Railway free tier or basic)
- Database: $0 (SQLite) or $15 (managed PostgreSQL)
- Domain: $12/year (optional)
- **Total: $0-20/month**

**Production Setup (Multiple Users):**
- Backend Hosting: $5-25 (depends on traffic)
- Database: $15 (managed PostgreSQL)
- CDN/DDoS Protection: $0 (Cloudflare free)
- Monitoring: $0 (UptimeRobot free)
- **Total: $20-40/month**

### Revenue Potential

If selling licenses at:
- $5/day = $150/month per user
- $20/week = $80/month per user
- $50/month = $50/month per user

**Break-even:** 1 user covers hosting costs

---

## Implementation Timeline

### Week 1: Backend Setup
- [ ] Set up FastAPI project structure
- [ ] Create database schema
- [ ] Implement /activate endpoint
- [ ] Implement /validate endpoint
- [ ] Add rate limiting and security
- [ ] Deploy to Railway/Render
- [ ] Test with Postman

### Week 2: Client Integration
- [ ] Create hardware fingerprinting module
- [ ] Create license service
- [ ] Create GUI dialog
- [ ] Integrate into ScriptRunner
- [ ] Add exception handling
- [ ] Write unit tests

### Week 3: Testing & Polish
- [ ] End-to-end testing
- [ ] Security audit
- [ ] Documentation
- [ ] User guide
- [ ] Package as EXE
- [ ] Test on different machines

### Week 4: Launch
- [ ] Set up payment processor (Gumroad)
- [ ] Create purchase page
- [ ] Configure webhooks
- [ ] Deploy production API
- [ ] Release v1.0

---

## Recommended Next Steps

1. **Choose Backend Hosting:** Railway.app for simplicity
2. **Set Up Database:** PostgreSQL on Railway
3. **Build API First:** Get /activate and /validate working
4. **Test with Postman:** Verify endpoints before client integration
5. **Implement Client:** Hardware fingerprinting → License service → GUI
6. **Integrate:** Add to ScriptRunner.__init__
7. **Test Thoroughly:** Multiple machines, expired keys, network errors
8. **Package EXE:** PyInstaller with license system included
9. **Set Up Payments:** Gumroad for easy checkout
10. **Launch:** Start selling licenses!

---

## Questions for Implementation

Before finalizing, please clarify:

1. **Pricing Strategy:** What license durations/prices are you planning?
   - Example: $5/day, $20/week, $50/month?

2. **Payment Processor:** Gumroad (easiest) or custom checkout?

3. **Refund Policy:** How to handle license revocation/refunds?

4. **Trial/Demo:** Offer free trial period? (e.g., 3 runs free)

5. **Updates:** How to handle bot updates with active licenses?

6. **Support:** Discord/email support for license issues?

Let me know your preferences and I'll refine the plan accordingly!
