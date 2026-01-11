"""
Hardware fingerprinting for machine identification.
Generates a unique, deterministic hash for the current machine.
"""

import hashlib
import platform
import uuid
import subprocess
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def get_machine_fingerprint() -> str:
    """
    Generate a unique fingerprint for this machine.

    The fingerprint is based on multiple hardware identifiers to ensure
    uniqueness while remaining deterministic across reboots.

    Returns:
        SHA256 hash of hardware identifiers (64 character hex string)
    """
    components = []

    # CPU info
    processor = platform.processor()
    if processor:
        components.append(processor)

    # MAC address of primary network interface
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff)
                    for i in range(0, 48, 8)][::-1])
    components.append(mac)

    # Platform-specific unique identifiers
    if platform.system() == "Windows":
        # Get motherboard UUID on Windows
        try:
            result = subprocess.check_output(
                'wmic csproduct get uuid',
                shell=True,
                stderr=subprocess.DEVNULL,
                timeout=5
            ).decode()
            uuid_line = result.split('\n')[1].strip()
            if uuid_line:
                components.append(uuid_line)
        except Exception as e:
            logger.debug(f"Failed to get Windows UUID: {e}")

        # Get Windows installation ID
        try:
            result = subprocess.check_output(
                'wmic os get SerialNumber',
                shell=True,
                stderr=subprocess.DEVNULL,
                timeout=5
            ).decode()
            serial = result.split('\n')[1].strip()
            if serial:
                components.append(serial)
        except Exception as e:
            logger.debug(f"Failed to get Windows serial: {e}")

    elif platform.system() == "Linux":
        # Get machine ID on Linux
        try:
            with open('/etc/machine-id', 'r') as f:
                machine_id = f.read().strip()
                if machine_id:
                    components.append(machine_id)
        except Exception as e:
            logger.debug(f"Failed to get Linux machine-id: {e}")

        # Get DMI UUID
        try:
            result = subprocess.check_output(
                ['cat', '/sys/class/dmi/id/product_uuid'],
                stderr=subprocess.DEVNULL,
                timeout=5
            ).decode().strip()
            if result:
                components.append(result)
        except Exception as e:
            logger.debug(f"Failed to get DMI UUID: {e}")

    elif platform.system() == "Darwin":  # macOS
        # Get hardware UUID on macOS
        try:
            result = subprocess.check_output(
                ['ioreg', '-rd1', '-c', 'IOPlatformExpertDevice'],
                stderr=subprocess.DEVNULL,
                timeout=5
            ).decode()
            for line in result.split('\n'):
                if 'IOPlatformUUID' in line:
                    hw_uuid = line.split('"')[-2]
                    components.append(hw_uuid)
                    break
        except Exception as e:
            logger.debug(f"Failed to get macOS UUID: {e}")

    # Fallback identifiers
    components.append(platform.node())  # hostname
    components.append(platform.machine())  # architecture
    components.append(platform.system())  # OS name

    # Remove empty components
    components = [c for c in components if c and c.strip()]

    # Create deterministic hash
    fingerprint_string = '|'.join(components)
    fingerprint_hash = hashlib.sha256(fingerprint_string.encode()).hexdigest()

    logger.debug(f"Generated fingerprint from {len(components)} components")

    return fingerprint_hash


def get_machine_info() -> dict:
    """
    Get human-readable machine information (for debugging).

    Returns:
        Dictionary with machine information
    """
    return {
        "system": platform.system(),
        "node": platform.node(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "fingerprint": get_machine_fingerprint()
    }


if __name__ == "__main__":
    # Test the fingerprint generation
    print("Machine Fingerprint:", get_machine_fingerprint())
    print("\nMachine Info:")
    for key, value in get_machine_info().items():
        print(f"  {key}: {value}")
