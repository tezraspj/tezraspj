"""Security helpers: password hashing (PBKDF2) and admin token check.

No third-party crypto dependencies — stdlib hashlib/hmac only.
"""
import hashlib
import hmac
import secrets

PBKDF2_ITERATIONS = 120_000
SALT_BYTES = 16


def hash_password(password: str) -> str:
    """Return 'pbkdf2$<iterations>$<salt_hex>$<hash_hex>'."""
    salt = secrets.token_bytes(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2${PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, TypeError):
        return False


def compare_token(provided: str, expected: str) -> bool:
    """Constant-time token comparison. Empty expected token = auth disabled."""
    if not expected:
        return False
    return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))
