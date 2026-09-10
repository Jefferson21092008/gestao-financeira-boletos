import re
from core.text import normalize_document

def cnpj_compact(value: str) -> str:
    return normalize_document(value)

def format_cnpj(value: str) -> str:
    c = cnpj_compact(value)
    if len(c) != 14:
        return value.strip()
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"

def validate_cnpj(value: str) -> bool:
    """Valida CNPJ numérico e o formato alfanumérico vigente desde 2026."""
    c = cnpj_compact(value)
    if not re.fullmatch(r"[A-Z0-9]{12}[0-9]{2}", c):
        return False
    if c.isdigit() and c == c[0] * 14:
        return False

    def char_value(ch: str) -> int:
        # Regra oficial do CNPJ alfanumérico: valor ASCII menos 48.
        return ord(ch) - 48

    def calc(base: str, weights: tuple[int, ...]) -> str:
        total = sum(char_value(ch) * w for ch, w in zip(base, weights))
        rem = total % 11
        return "0" if rem in (0, 1) else str(11 - rem)

    dv1 = calc(c[:12], (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))
    dv2 = calc(c[:12] + dv1, (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))
    return c[-2:] == dv1 + dv2
