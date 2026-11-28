"""Security helper tests: password hashing and token comparison."""
from app.security import compare_token, hash_password, verify_password


def test_password_hash_roundtrip():
    stored = hash_password("s3cret-Passw0rd!")
    assert stored.startswith("pbkdf2$")
    assert verify_password("s3cret-Passw0rd!", stored) is True
    assert verify_password("wrong-password", stored) is False


def test_password_hashes_are_salted():
    a = hash_password("same-password")
    b = hash_password("same-password")
    assert a != b  # different salts


def test_verify_malformed_stored_value():
    assert verify_password("x", "not-a-hash") is False
    assert verify_password("x", "") is False


def test_compare_token():
    assert compare_token("abc123", "abc123") is True
    assert compare_token("abc123", "other") is False
    assert compare_token("", "expected") is False
    # empty expected token = auth disabled → always False (deny)
    assert compare_token("anything", "") is False
