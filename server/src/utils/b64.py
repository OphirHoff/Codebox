"""
Base64 encoding and decoding utilities with UTF-8 support.

This module provides simplified wrappers around Python's base64 library,
handling UTF-8 encoding/decoding automatically. Useful for:
- Encoding text for transmission in protocols that require ASCII
- Storing binary data in text-based formats
- Converting between string and base64 representations
"""

import base64

def base64_encode(to_encode: str) -> bytes:
    """
    Encode a string to base64 using UTF-8 encoding.

    Args:
        to_encode: String to encode

    Returns:
        bytes: Base64 encoded bytes
    """
    return base64.b64encode(to_encode.encode('utf-8'))

def base64_decode(encoded: bytes) -> str:
    """
    Decode base64 bytes to a UTF-8 string.

    Args:
        encoded: Base64 encoded bytes to decode

    Returns:
        str: Decoded UTF-8 string
    """
    return base64.b64decode(encoded).decode('utf-8')