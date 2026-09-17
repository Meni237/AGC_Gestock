import hashlib
import os

def hash_password(password: str) -> str:
    # Génération d'un sel aléatoire de 16 octets
    salt = os.urandom(16)
    # Hachage sécurisé PBKDF2 avec SHA-256
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    # Stockage sous forme : salt_hex$hash_hex
    return f"{salt.hex()}${pwd_hash.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        salt_hex, stored_hash = hashed_password.split('$')
        salt = bytes.fromhex(salt_hex)
        # Recalcul du hachage avec le même sel
        pwd_hash = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, 100000)
        return pwd_hash.hex() == stored_hash
    except Exception:
        return False