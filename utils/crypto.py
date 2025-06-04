from base64 import urlsafe_b64encode, urlsafe_b64decode
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
import os, json

ITER = 100_000

def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=ITER,
    )
    return kdf.derive(password.encode())

def encrypt(payload: dict, password: str) -> str:
    salt = os.urandom(16)
    key  = _derive_key(password, salt)
    aes  = AESGCM(key)
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, json.dumps(payload).encode(), b"")
    blob = salt + nonce + ct
    return urlsafe_b64encode(blob).decode()

def decrypt(token: str, password: str) -> dict :
    try:
        blob  = urlsafe_b64decode(token.encode())
        salt, nonce, ct = blob[:16], blob[16:28], blob[28:]
        key   = _derive_key(password, salt)
        aes   = AESGCM(key)
        data  = aes.decrypt(nonce, ct, b"")
        return json.loads(data)
    except Exception:
        return None
