from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad

from utils.tcp_by_size import send_one_message, recv_one_message

import pickle

KEYS_DIR = "secrets\\keys"

def gen_rsa_keys():
    """Generates public & private RSA keys and stores them locally."""

    # Generate public and private keys
    rsa_key = RSA.generate(2048)
    private_key = rsa_key
    public_key = rsa_key.publickey()

    # Save keys locally (PEM format)
    with open(f"{KEYS_DIR}\\private_key.pem", "wb") as private_file:
        private_file.write(private_key.export_key())
    
    with open(f"{KEYS_DIR}\\public_key.pem", "wb") as public_file:
        public_file.write(public_key.export_key())

def load_rsa_public_key():
    """Loads the generated public RSA key from storage."""

    with open(f"{KEYS_DIR}\\public_key.pem", "rb") as public_file:
        public_key = RSA.import_key(public_file.read())
    
    return public_key

def load_rsa_private_key():
    """Loads the generated private RSA key from storage."""
    with open(f"{KEYS_DIR}\\private_key.pem", "rb") as private_file:
        private_key = RSA.import_key(private_file.read())

    return private_key

def gen_aes_key(size=256):
    """Generates a random AES key."""
    return get_random_bytes(size // 8)

def rsa_encrypt(data, public_key):
    """Encryptes a message RSA using a public key."""

    if type(data) != bytes:
        data = data.encode()

    # Encrypt message using the RSA public key
    rsa_cipher = PKCS1_OAEP.new(public_key)
    encrypted_data = rsa_cipher.encrypt(data)

    return encrypted_data

def rsa_decrypt(encrypted_data, private_key):
    """Decryptes an RSA-encrypted message a private key."""

    # Decrypt message using the RSA private key
    rsa_decipher = PKCS1_OAEP.new(private_key)
    decrypted_data = rsa_decipher.decrypt(encrypted_data)

    return decrypted_data

def aes_encrypt(data, aes_key):
    """
    Encryptes data with AES-CBC using a given key.

    Returns: tuple consisting of the encrypted data and iv (cipher, iv)
    """

    cipher_aes = AES.new(aes_key, AES.MODE_CBC)
    iv = cipher_aes.iv
    cipher = cipher_aes.encrypt(pad(data, AES.block_size))

    return cipher, iv

def aes_decrypt(cipher, aes_key, iv):
    """Decryptes data with AES-CBC using a given key and iv."""

    cipher_aes_dec = AES.new(aes_key, AES.MODE_CBC, iv)
    decrypted_data = unpad(cipher_aes_dec.decrypt(cipher), AES.block_size)

    return decrypted_data

def send_secure(sock, data, aes_key):
    """Encryptes data to send with AES and sends."""
    enc_data, iv = aes_encrypt(data, aes_key)
    to_send = {
        'data': enc_data,
        'iv': iv
    }

    send_one_message(sock, pickle.dumps(to_send))

def recv_secure(sock, aes_key):
    """Receives AES-encrypted data and decryptes."""
    msg = recv_one_message(sock, return_type='bytes')

    # Extract encrypted data and iv from message
    data = pickle.loads(msg)
    enc_data = data.get('data')
    iv = data.get('iv')

    # return decrypted data
    return aes_decrypt(enc_data, aes_key, iv)