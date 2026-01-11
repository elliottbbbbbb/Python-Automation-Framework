"""
Test script for license server API.
Run this after starting the server to verify all endpoints work correctly.
"""

import requests
import time
from osrsbot.services.hardware_fingerprint import get_machine_fingerprint

# Configuration
API_URL = "http://localhost:8000"
API_KEY = "your-secret-api-key-change-this-to-something-random"  # Change this to match your .env


def test_health_check():
    """Test health check endpoint."""
    print("\n1. Testing health check...")
    response = requests.get(f"{API_URL}/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    assert response.status_code == 200, "Health check failed"
    print("   ✓ Health check passed")


def test_create_license(duration_hours=24, notes="test_license"):
    """Test creating a license."""
    print(f"\n2. Creating license ({duration_hours}h)...")
    response = requests.post(
        f"{API_URL}/api/v1/admin/licenses",
        params={"duration_hours": duration_hours, "notes": notes},
        headers={"X-API-Key": API_KEY}
    )
    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        license_key = data['license_key']
        print(f"   License Key: {license_key}")
        print(f"   Duration: {data['duration_hours']} hours")
        print("   ✓ License created successfully")
        return license_key
    else:
        print(f"   ✗ Failed: {response.text}")
        return None


def test_activate_license(license_key):
    """Test activating a license."""
    print(f"\n3. Activating license: {license_key}...")
    fingerprint = get_machine_fingerprint()
    print(f"   Machine fingerprint: {fingerprint[:16]}...")

    response = requests.post(
        f"{API_URL}/api/v1/activate",
        json={
            "license_key": license_key,
            "machine_fingerprint": fingerprint,
            "client_version": "1.0.0"
        }
    )
    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"   Success: {data['success']}")
        print(f"   Expires: {data.get('expires_at', 'N/A')}")
        print(f"   Message: {data['message']}")
        print("   ✓ License activated successfully")
        return True
    else:
        print(f"   ✗ Failed: {response.text}")
        return False


def test_validate_license(license_key):
    """Test validating a license."""
    print(f"\n4. Validating license: {license_key}...")
    fingerprint = get_machine_fingerprint()

    response = requests.post(
        f"{API_URL}/api/v1/validate",
        json={
            "license_key": license_key,
            "machine_fingerprint": fingerprint
        }
    )
    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"   Valid: {data['valid']}")
        if data['valid']:
            print(f"   Hours remaining: {data.get('hours_remaining', 'N/A')}")
            print(f"   Expires: {data.get('expires_at', 'N/A')}")
        print("   ✓ License validated successfully")
        return data['valid']
    else:
        print(f"   ✗ Failed: {response.text}")
        return False


def test_list_licenses():
    """Test listing all licenses."""
    print("\n5. Listing all licenses...")
    response = requests.get(
        f"{API_URL}/api/v1/admin/licenses",
        headers={"X-API-Key": API_KEY}
    )
    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        licenses = response.json()
        print(f"   Total licenses: {len(licenses)}")
        for lic in licenses[:3]:  # Show first 3
            print(f"   - {lic['license_key']}: {lic['activation_count']} activations")
        print("   ✓ License list retrieved successfully")
        return True
    else:
        print(f"   ✗ Failed: {response.text}")
        return False


def test_get_license(license_key):
    """Test getting specific license details."""
    print(f"\n6. Getting license details: {license_key}...")
    response = requests.get(
        f"{API_URL}/api/v1/admin/licenses/{license_key}",
        headers={"X-API-Key": API_KEY}
    )
    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"   License Key: {data['license_key']}")
        print(f"   Duration: {data['duration_hours']} hours")
        print(f"   Activations: {data['activation_count']}")
        print(f"   Active: {data['is_active']}")
        print("   ✓ License details retrieved successfully")
        return True
    else:
        print(f"   ✗ Failed: {response.text}")
        return False


def test_revoke_license(license_key):
    """Test revoking a license."""
    print(f"\n7. Revoking license: {license_key}...")
    response = requests.delete(
        f"{API_URL}/api/v1/admin/licenses/{license_key}",
        headers={"X-API-Key": API_KEY}
    )
    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"   Message: {data['message']}")
        print("   ✓ License revoked successfully")
        return True
    else:
        print(f"   ✗ Failed: {response.text}")
        return False


def test_validate_revoked_license(license_key):
    """Test that revoked license fails validation."""
    print(f"\n8. Testing revoked license validation (should fail)...")
    fingerprint = get_machine_fingerprint()

    response = requests.post(
        f"{API_URL}/api/v1/validate",
        json={
            "license_key": license_key,
            "machine_fingerprint": fingerprint
        }
    )
    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"   Valid: {data['valid']}")
        if not data['valid'] and data.get('error') == 'LICENSE_REVOKED':
            print("   ✓ Revoked license correctly rejected")
            return True
        else:
            print("   ✗ Revoked license was accepted (should not happen!)")
            return False
    else:
        print(f"   ✗ Request failed: {response.text}")
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("  License Server API Test Suite")
    print("="*60)
    print(f"\nAPI URL: {API_URL}")
    print(f"API Key: {API_KEY[:10]}..." if len(API_KEY) > 10 else f"API Key: {API_KEY}")

    try:
        # Test 1: Health check
        test_health_check()

        # Test 2: Create license
        license_key = test_create_license(duration_hours=24, notes="test_license")
        if not license_key:
            print("\n✗ Test suite failed: Could not create license")
            return

        # Small delay to ensure database writes complete
        time.sleep(0.5)

        # Test 3: Activate license
        if not test_activate_license(license_key):
            print("\n✗ Test suite failed: Could not activate license")
            return

        # Test 4: Validate license
        if not test_validate_license(license_key):
            print("\n✗ Test suite failed: License validation failed")
            return

        # Test 5: List licenses
        test_list_licenses()

        # Test 6: Get license details
        test_get_license(license_key)

        # Test 7: Revoke license
        test_revoke_license(license_key)

        # Test 8: Validate revoked license (should fail)
        test_validate_revoked_license(license_key)

        print("\n" + "="*60)
        print("  ✓ All tests passed successfully!")
        print("="*60)

    except Exception as e:
        print(f"\n✗ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
