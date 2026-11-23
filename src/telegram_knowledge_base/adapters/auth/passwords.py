import base64
import hashlib
import hmac
import os

_ITERATIONS = 200_000
_MINIMUM_PASSWORD_LENGTH = 12


def hash_password(password: str) -> str:
    if len(password.strip()) < _MINIMUM_PASSWORD_LENGTH:
        raise ValueError("The password must contain at least 12 characters.")
    salt = os.urandom(16)
    digest = _derive(password, salt)
    return (
        "pbkdf2_sha256$"
        f"{_ITERATIONS}$"
        f"{base64.urlsafe_b64encode(salt).decode('ascii')}$"
        f"{base64.urlsafe_b64encode(digest).decode('ascii')}"
    )


def verify_password(password: str, verifier: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = verifier.split("$")
        if algorithm != "pbkdf2_sha256":
            raise ValueError
        iterations = int(iterations_text)
        if iterations < 1:
            raise ValueError
        salt = base64.b64decode(salt_text, altchars=b"-_", validate=True)
        expected = base64.b64decode(digest_text, altchars=b"-_", validate=True)
    except (ValueError, TypeError):
        raise ValueError("The stored password verifier is invalid.") from None
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def _derive(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
