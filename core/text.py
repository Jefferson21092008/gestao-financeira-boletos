import re
import unicodedata
from difflib import SequenceMatcher


def digits_only(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", (value or "").strip().lower())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return " ".join(normalized.split())


def text_similarity(a: str, b: str) -> float:
    na, nb = normalize_text(a), normalize_text(b)
    if not na or not nb:
        return 0.0
    if na in nb or nb in na:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


def normalize_document(value: str) -> str:
    """Mantém letras/números para CNPJ alfanumérico e remove pontuação."""
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())
