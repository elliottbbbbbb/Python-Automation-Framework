# OSRS Bot Security Assessment Report

**Assessment Date**: December 12, 2025
**Assessed By**: Security Analysis Agent
**Severity Scale**: CRITICAL > HIGH > MEDIUM > LOW

---

## Executive Summary

This security assessment identifies **6 critical and high-priority security vulnerabilities** in the OSRS Bot codebase. The most critical issues involve credential exposure, lack of input validation, and information disclosure through logging.

**Risk Level**: MEDIUM-HIGH

**Critical Findings**: 2
**High Priority Findings**: 2
**Medium Priority Findings**: 2

**Recommendation**: Address critical and high-priority issues before deployment or public release.

---

## Table of Contents

1. [Critical Security Issues](#1-critical-security-issues)
2. [High Priority Issues](#2-high-priority-issues)
3. [Medium Priority Issues](#3-medium-priority-issues)
4. [Security Best Practices](#4-security-best-practices)
5. [Remediation Roadmap](#5-remediation-roadmap)

---

## 1. Critical Security Issues

### Issue #1: Credential and Account Information Exposure

**Severity**: 🔴 CRITICAL

**Location**:
- [config.json](../config.json) - Lines 2-4
- [src/osrsbot/models/config.py](../src/osrsbot/models/config.py)

**Description**:
Account names and window titles are stored in plain text in the configuration file, which is committed to version control.

**Vulnerable Code**:
```json
{
  "account_name": "61grouphunt",
  "window_title": "RuneLite - 61grouphunt",
  ...
}
```

**Attack Vector**:
1. Repository made public or leaked
2. Attacker gains access to config file
3. Account name revealed
4. Account can be targeted for tracking or harassment

**Risk Assessment**:
- **Confidentiality**: High - Account identity exposed
- **Integrity**: Medium - Could enable targeted attacks
- **Availability**: Low - No direct service impact

**Proof of Concept**:
```bash
# If repository is public
git clone https://github.com/user/OSRSbot
cat config.json | grep account_name
# Output: "account_name": "61grouphunt"
```

**Remediation**:

**Immediate (Priority 1)**:
1. Add `config.json` to `.gitignore`
2. Remove `config.json` from git history
3. Create `config.example.json` template

```bash
# Remove from git history
git rm --cached config.json
echo "config.json" >> .gitignore
git commit -m "Remove sensitive config from git"

# Create template
cp config.json config.example.json
# Edit config.example.json to remove sensitive values
```

**Long-term (Priority 2)**:
1. Use environment variables for sensitive data
2. Implement secrets management

```python
import os
from dotenv import load_dotenv

load_dotenv()

account_name = os.getenv("OSRS_ACCOUNT_NAME")
if not account_name:
    raise ValueError("OSRS_ACCOUNT_NAME environment variable not set")

config = {
    "account_name": account_name,
    ...
}
```

**Status**: ❌ UNRESOLVED

---

### Issue #2: Configuration File in Version Control

**Severity**: 🔴 CRITICAL

**Location**:
- Root `.gitignore` file (missing entry)
- [config.json](../config.json) committed to repository

**Description**:
Sensitive configuration file is tracked by git and committed to version control history.

**Risk Assessment**:
- Even if removed now, exists in git history
- Anyone with repository access can view historical commits
- Difficult to fully remove from history once pushed

**Remediation**:

**Immediate**:
```bash
# Check if config.json is tracked
git ls-files | grep config.json

# If tracked, remove from index
git rm --cached config.json

# Add to .gitignore
echo "" >> .gitignore
echo "# Sensitive configuration" >> .gitignore
echo "config.json" >> .gitignore
echo ".env" >> .gitignore
echo "*.env" >> .gitignore
echo ".env.local" >> .gitignore

# Commit changes
git add .gitignore
git commit -m "feat: Add sensitive files to .gitignore"
```

**Advanced** (if already pushed to remote):
```bash
# WARNING: This rewrites history - coordinate with team first
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch config.json" \
  --prune-empty --tag-name-filter cat -- --all

# Force push (DANGEROUS - inform team)
git push --force --all
```

**Alternative**: Treat all historical commits as compromised and rotate any credentials.

**Status**: ❌ UNRESOLVED

---

## 2. High Priority Issues

### Issue #3: Missing Input Validation

**Severity**: 🟠 HIGH

**Location**:
- [src/osrsbot/commands/game_actions.py](../src/osrsbot/commands/game_actions.py) - Line ~227

**Description**:
User input is passed directly to `pyautogui.write()` without validation or sanitization.

**Vulnerable Code**:
```python
def type_text(self, text: str) -> None:
    """Type text into the game client."""
    pyautogui.write(text)  # No validation!
```

**Attack Vector**:
1. Malicious or unexpected input passed to `type_text()`
2. Special characters or control sequences sent to game
3. Could trigger unintended game commands
4. Could type passwords or sensitive data if input is not controlled

**Example Attack**:
```python
# Attacker provides malicious input
malicious_input = "item_name\n/logout\npassword123"
actions.type_text(malicious_input)
# Bot types item name, then executes logout command, then types password
```

**Risk Assessment**:
- **Confidentiality**: High - Could leak sensitive data
- **Integrity**: High - Could execute unintended commands
- **Availability**: Medium - Could disrupt bot operation

**Remediation**:

```python
import re
from typing import Optional

class InputValidator:
    """Validates user input before sending to game"""

    # Whitelist of allowed characters
    ALLOWED_CHARS = re.compile(r'^[a-zA-Z0-9 _\-]+$')

    # Maximum length
    MAX_LENGTH = 50

    @staticmethod
    def validate_text(text: str) -> str:
        """Validate and sanitize text input"""
        if not text:
            raise ValueError("Text cannot be empty")

        if len(text) > InputValidator.MAX_LENGTH:
            raise ValueError(f"Text too long: {len(text)} > {InputValidator.MAX_LENGTH}")

        if not InputValidator.ALLOWED_CHARS.match(text):
            raise ValueError(f"Invalid characters in text: {text}")

        # Remove leading/trailing whitespace
        text = text.strip()

        return text


# Updated game_actions.py
def type_text(self, text: str) -> None:
    """Type text into the game client."""
    validated_text = InputValidator.validate_text(text)
    logger.info(f"Typing validated text: {validated_text}")
    pyautogui.write(validated_text)
```

**Testing**:
```python
def test_input_validation():
    # Valid input
    assert InputValidator.validate_text("sword") == "sword"
    assert InputValidator.validate_text("dragon_bones") == "dragon_bones"

    # Invalid input
    with pytest.raises(ValueError):
        InputValidator.validate_text("item\n/logout")  # Newline not allowed

    with pytest.raises(ValueError):
        InputValidator.validate_text("item;/logout")  # Semicolon not allowed

    with pytest.raises(ValueError):
        InputValidator.validate_text("a" * 100)  # Too long
```

**Status**: ❌ UNRESOLVED

---

### Issue #4: Information Disclosure in Logs

**Severity**: 🟠 HIGH

**Location**:
- Throughout codebase (364 logging calls)
- [src/osrsbot/core/game_interface.py](../src/osrsbot/core/game_interface.py) - Window title logging
- [src/osrsbot/services/anti_ban_service.py](../src/osrsbot/services/anti_ban_service.py) - Break timing logs

**Description**:
Sensitive information including account names, window titles, and precise timing patterns are logged in clear text.

**Vulnerable Code**:
```python
# game_interface.py
logger.info(f"Successfully attached to window: {self.window.title}")
# Logs: "Successfully attached to window: RuneLite - 61grouphunt"

# anti_ban_service.py
logger.info(f"===== TAKING SCHEDULED BREAK ({duration/60:.1f} minutes) =====")
# Logs exact break duration - enables pattern analysis
```

**Attack Vector**:
1. Log files captured by monitoring software
2. Pattern analysis reveals bot behavior
3. Account names identified
4. Timing patterns analyzed for detection

**Risk Assessment**:
- **Confidentiality**: High - Account identity exposed
- **Integrity**: Low
- **Availability**: Medium - Could lead to account ban

**Remediation**:

```python
import re
import hashlib

class LogRedactor:
    """Redacts sensitive information from log messages"""

    @staticmethod
    def redact_account_name(message: str) -> str:
        """Replace account names with hash"""
        # Pattern: "RuneLite - <account>"
        pattern = r'RuneLite - ([a-zA-Z0-9_]+)'

        def replacer(match):
            account = match.group(1)
            # Hash account name for privacy
            account_hash = hashlib.sha256(account.encode()).hexdigest()[:8]
            return f"RuneLite - ****{account_hash}"

        return re.sub(pattern, replacer, message)

    @staticmethod
    def redact_timing(message: str) -> str:
        """Reduce precision of timing information"""
        # Replace precise timings with ranges
        # "2.3 minutes" -> "2-3 minutes"
        pattern = r'(\d+\.\d+) minutes'

        def replacer(match):
            precise_time = float(match.group(1))
            rounded_low = int(precise_time)
            rounded_high = rounded_low + 1
            return f"{rounded_low}-{rounded_high} minutes"

        return re.sub(pattern, replacer, message)


# Custom logging formatter
class RedactingFormatter(logging.Formatter):
    """Formatter that redacts sensitive information"""

    def format(self, record):
        msg = super().format(record)
        msg = LogRedactor.redact_account_name(msg)
        msg = LogRedactor.redact_timing(msg)
        return msg


# Setup logging with redaction
handler = logging.StreamHandler()
handler.setFormatter(RedactingFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
```

**Status**: ❌ UNRESOLVED

---

## 3. Medium Priority Issues

### Issue #5: System Command Execution Risk

**Severity**: 🟡 MEDIUM

**Location**:
- [src/osrsbot/services/ocr_service.py](../src/osrsbot/services/ocr_service.py)
- Hard-coded Tesseract path

**Description**:
Hard-coded path to Tesseract executable with subprocess calls could be vulnerable if path is compromised.

**Vulnerable Code**:
```python
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# Subprocess calls via pytesseract wrapper
```

**Attack Vector**:
1. Attacker gains write access to `C:\Program Files\Tesseract-OCR\`
2. Replaces `tesseract.exe` with malicious executable
3. Bot executes malicious code via subprocess

**Risk Assessment**:
- **Confidentiality**: High - Could exfiltrate data
- **Integrity**: High - Could modify system
- **Availability**: High - Could crash or disable bot
- **Likelihood**: Low - Requires admin privileges

**Remediation**:

```python
import os
import hashlib

class ExecutableValidator:
    """Validates external executables before use"""

    TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    # Optional: Known good checksums (update when Tesseract updates)
    KNOWN_CHECKSUMS = {
        "5.3.0": "abc123...",  # Example
    }

    @staticmethod
    def validate_tesseract() -> str:
        """Validate Tesseract executable exists and is valid"""
        path = ExecutableValidator.TESSERACT_PATH

        # Check existence
        if not os.path.exists(path):
            raise FileNotFoundError(f"Tesseract not found at: {path}")

        # Check it's a file
        if not os.path.isfile(path):
            raise ValueError(f"Tesseract path is not a file: {path}")

        # Check permissions (Windows)
        if not os.access(path, os.X_OK):
            raise PermissionError(f"Tesseract is not executable: {path}")

        # Optional: Verify checksum
        # checksum = ExecutableValidator.get_file_checksum(path)
        # if checksum not in ExecutableValidator.KNOWN_CHECKSUMS.values():
        #     logger.warning(f"Tesseract checksum unknown: {checksum}")

        logger.info(f"Tesseract validated at: {path}")
        return path

    @staticmethod
    def get_file_checksum(filepath: str) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


# In OCRService.__init__
tesseract_path = ExecutableValidator.validate_tesseract()
pytesseract.pytesseract.tesseract_cmd = tesseract_path
```

**Status**: ❌ UNRESOLVED

---

### Issue #6: Window Handle Validation Missing

**Severity**: 🟡 MEDIUM

**Location**:
- [src/osrsbot/services/virtual_mouse_service.py](../src/osrsbot/services/virtual_mouse_service.py)
- [src/osrsbot/core/game_interface.py](../src/osrsbot/core/game_interface.py)

**Description**:
No validation of window handle validity or RuneLite-specific properties before sending input.

**Vulnerable Code**:
```python
# game_interface.py
def _find_window(self):
    windows = gw.getWindowsWithTitle(window_title)
    if not windows:
        raise Exception(f"Window not found: {window_title}")
    return windows[0]  # No further validation
```

**Attack Vector**:
1. Another application has similar window title
2. Bot sends input to wrong application
3. Sensitive commands or data sent to wrong app

**Risk Assessment**:
- **Confidentiality**: Medium - Could leak data to wrong app
- **Integrity**: Medium - Could execute commands in wrong app
- **Availability**: Low
- **Likelihood**: Low - Requires window title collision

**Remediation**:

```python
class WindowValidator:
    """Validates game window before sending input"""

    REQUIRED_TITLE_PATTERN = r"RuneLite.*"
    REQUIRED_CLASS_NAME = "SunAwtFrame"  # RuneLite uses Java/AWT

    @staticmethod
    def validate_window(window) -> bool:
        """Validate window is actually RuneLite"""
        import re

        # Check title pattern
        if not re.match(WindowValidator.REQUIRED_TITLE_PATTERN, window.title):
            logger.warning(f"Window title doesn't match RuneLite pattern: {window.title}")
            return False

        # Check if window is visible and active
        if not window.visible:
            logger.warning("Window is not visible")
            return False

        # Additional checks could include:
        # - Process name verification
        # - Window class name
        # - Window dimensions (RuneLite has specific default size)

        logger.debug(f"Window validated: {window.title}")
        return True


# In game_interface.py
def _find_window(self):
    windows = gw.getWindowsWithTitle(window_title)

    for window in windows:
        if WindowValidator.validate_window(window):
            logger.info(f"Found valid RuneLite window: {window.title}")
            return window

    raise Exception(f"No valid RuneLite window found with title: {window_title}")
```

**Status**: ❌ UNRESOLVED

---

## 4. Security Best Practices

### 4.1 Secrets Management

**Current State**: Secrets in plain text config files ❌

**Recommendation**:
1. Use environment variables for all sensitive data
2. Use `.env` files (with `.gitignore`)
3. Consider secrets management tools for production

**Implementation**:
```python
# .env file (add to .gitignore)
OSRS_ACCOUNT_NAME=myaccount
OSRS_WINDOW_TITLE=RuneLite - myaccount

# Load in code
from dotenv import load_dotenv
import os

load_dotenv()

account_name = os.getenv("OSRS_ACCOUNT_NAME")
window_title = os.getenv("OSRS_WINDOW_TITLE")
```

### 4.2 Input Validation

**Current State**: No input validation ❌

**Recommendation**:
1. Validate all external input
2. Use whitelists instead of blacklists
3. Sanitize before processing

**Validation Checklist**:
- [ ] Type checking (str, int, float)
- [ ] Length limits
- [ ] Character whitelist
- [ ] Range checking for numbers
- [ ] Path traversal prevention

### 4.3 Logging Security

**Current State**: Sensitive data in logs ❌

**Recommendation**:
1. Implement log redaction
2. Use structured logging
3. Sanitize before logging
4. Different log levels for different environments

**Best Practices**:
```python
# Bad
logger.info(f"Account: {account_name}")

# Good
logger.info(f"Account: {hash_account(account_name)}")

# Better
logger.info("Account authenticated", extra={"account_hash": hash_account(account_name)})
```

### 4.4 Configuration Security

**Current State**: No schema validation ❌

**Recommendation**:
1. Use schema validation (pydantic)
2. Type checking
3. Bounds checking
4. Encryption for sensitive config

**Implementation**:
```python
from pydantic import BaseModel, Field, validator

class MouseConfig(BaseModel):
    min_speed: float = Field(ge=0.1, le=2.0)
    max_speed: float = Field(ge=0.1, le=2.0)
    overshoot_chance: float = Field(ge=0.0, le=1.0)

    @validator('max_speed')
    def max_greater_than_min(cls, v, values):
        if 'min_speed' in values and v < values['min_speed']:
            raise ValueError('max_speed must be >= min_speed')
        return v

# Load and validate
config_data = json.load(open("config.json"))
mouse_config = MouseConfig(**config_data["mouse"])
```

### 4.5 Dependency Security

**Current State**: No dependency scanning ⚠️

**Recommendation**:
1. Regular dependency updates
2. Vulnerability scanning
3. Pin dependencies to specific versions

**Tools**:
```bash
# Check for vulnerabilities
pip install safety
safety check

# Update dependencies
pip install --upgrade pip-tools
pip-compile --upgrade

# Audit dependencies
pip-audit
```

---

## 5. Remediation Roadmap

### Phase 1: Critical Issues (Week 1)

**Priority**: IMMEDIATE

Tasks:
1. [ ] Add `config.json` to `.gitignore`
2. [ ] Remove `config.json` from git history
3. [ ] Create `config.example.json` template
4. [ ] Implement environment variable support
5. [ ] Add input validation to `game_actions.py`
6. [ ] Document secrets management process

**Estimated Effort**: 8 hours

---

### Phase 2: High Priority Issues (Week 2)

**Priority**: HIGH

Tasks:
1. [ ] Implement log redaction
2. [ ] Add custom logging formatter
3. [ ] Validate Tesseract executable
4. [ ] Add window validation
5. [ ] Update logging throughout codebase

**Estimated Effort**: 12 hours

---

### Phase 3: Medium Priority Issues (Week 3-4)

**Priority**: MEDIUM

Tasks:
1. [ ] Implement config schema validation (pydantic)
2. [ ] Add comprehensive input validation
3. [ ] Implement executable checksum verification
4. [ ] Add security unit tests
5. [ ] Document security practices

**Estimated Effort**: 16 hours

---

### Phase 4: Security Hardening (Ongoing)

**Priority**: ONGOING

Tasks:
1. [ ] Regular dependency updates
2. [ ] Vulnerability scanning
3. [ ] Security code reviews
4. [ ] Penetration testing
5. [ ] Security monitoring

**Estimated Effort**: 2-4 hours/month

---

## 6. Security Testing

### 6.1 Test Cases

```python
# test_security.py

def test_config_not_in_git():
    """Ensure config.json is not tracked by git"""
    result = subprocess.run(
        ["git", "ls-files", "config.json"],
        capture_output=True,
        text=True
    )
    assert result.stdout == "", "config.json should not be tracked by git"


def test_input_validation_blocks_newlines():
    """Ensure input validation blocks newline characters"""
    from osrsbot.utils.input_validator import InputValidator

    with pytest.raises(ValueError):
        InputValidator.validate_text("item\n/logout")


def test_log_redaction():
    """Ensure logs redact account names"""
    from osrsbot.utils.log_redactor import LogRedactor

    message = "Successfully attached to window: RuneLite - myaccount"
    redacted = LogRedactor.redact_account_name(message)

    assert "myaccount" not in redacted
    assert "****" in redacted
```

### 6.2 Security Checklist

Before deployment:
- [ ] All secrets in environment variables
- [ ] Config files in `.gitignore`
- [ ] Input validation implemented
- [ ] Logs redacted
- [ ] Dependencies updated
- [ ] Security tests passing
- [ ] Code review completed

---

## 7. Incident Response

### 7.1 If Credentials Leaked

1. **Immediate**:
   - Change affected account passwords
   - Revoke any API keys or tokens
   - Monitor account for suspicious activity

2. **Short-term**:
   - Review git history for other leaks
   - Rotate all secrets
   - Update security practices

3. **Long-term**:
   - Implement secrets management
   - Regular security audits
   - Team security training

### 7.2 If Repository Compromised

1. **Assess scope** of compromise
2. **Revoke access** for compromised accounts
3. **Rotate all secrets** and credentials
4. **Review commit history** for malicious changes
5. **Notify users** if user data affected
6. **Update security practices**

---

## Conclusion

The OSRS Bot codebase has **significant security vulnerabilities** that should be addressed before public release or deployment. The critical issues involving credential exposure and input validation pose immediate risks.

**Overall Security Rating**: 5/10 - MEDIUM RISK

**Recommendation**: Follow the remediation roadmap to address critical and high-priority issues within 2-3 weeks.

**Next Steps**:
1. Implement Phase 1 (Critical Issues) immediately
2. Schedule Phase 2 (High Priority) for next week
3. Plan Phase 3 (Medium Priority) for next month
4. Establish ongoing security practices

---

**Report Prepared By**: Security Analysis Agent
**Date**: December 12, 2025
**Version**: 1.0
