"""
Password hashing and security utilities.

This module provides secure password hashing functionality using a combination of:
- SHA-256 hashing
- Unique salt per password (using bcrypt's salt generation)
- Application-wide pepper (loaded from environment variables)

The pepper adds an additional layer of security by ensuring that even if the database
is compromised, the hashed passwords cannot be cracked without access to the pepper.

Note:
    The PEPPER environment variable must be base64 encoded in the .env file.
"""

import os
import base64
import hashlib
import bcrypt
from dotenv import load_dotenv

# Load & Decode pepper
load_dotenv()
encoded_pepper = os.getenv("PEPPER")
PEPPER = base64.b64decode(encoded_pepper)

def hash_password(password: str, salt: bytes) -> str:
    """
    Hash a password using SHA-256 with salt and pepper.

    Args:
        password: The plain text password to hash
        salt: Unique salt bytes for this password

    Returns:
        str: Hexadecimal representation of the hashed password
    """
    return hashlib.sha256(password.encode()+salt+PEPPER).hexdigest()

def generate_salt_hash(password: str) -> tuple[str, bytes]:
    """
    Generate a new salt and hash for a password.

    Args:
        password: The plain text password to hash

    Returns:
        tuple: (hashed_password, salt) where:
            - hashed_password is the hex string of the hashed password
            - salt is the bytes used for salting
    """
    salt = bcrypt.gensalt()
    hashed_pw = hash_password(password, salt)
    return hashed_pw, salt