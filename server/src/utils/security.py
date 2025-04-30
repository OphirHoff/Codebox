import os
import base64
import hashlib
import bcrypt
from dotenv import load_dotenv

# Load & Decode pepper
load_dotenv()
encoded_pepper = os.getenv("PEPPER")
PEPPER = base64.b64decode(encoded_pepper)

def hash_password(password: str, salt: bytes):
    return hashlib.sha256(password.encode()+salt+PEPPER).hexdigest()

def generate_salt_hash(password: str):
    salt = bcrypt.gensalt()
    hashed_pw = hash_password(password, salt)
    return hashed_pw, salt