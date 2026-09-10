import hashlib
import hmac
import os

from config import MIN_PASSWORD_LENGTH, PBKDF2_ITERATIONS


def hash_password(password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    if salt is None:
        salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return digest, salt


def verify_password(password: str, stored_hash: bytes, salt: bytes) -> bool:
    digest, _ = hash_password(password, salt)
    return hmac.compare_digest(digest, stored_hash)


def validate_new_password(password: str) -> None:
    """Política simples para uso local: longa o suficiente, sem regras artificiais."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"A senha deve ter pelo menos {MIN_PASSWORD_LENGTH} caracteres.")
    if password.strip() != password:
        raise ValueError("A senha não pode começar ou terminar com espaços.")
    if password.lower() in {"admin123", "12345678", "password", "senha123"}:
        raise ValueError("Escolha uma senha menos previsível.")
