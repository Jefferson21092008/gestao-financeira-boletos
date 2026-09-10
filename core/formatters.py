from datetime import datetime
from decimal import Decimal, InvalidOperation

from config import DATE_FMT_DB, DATE_FMT_UI
from core.finance import as_decimal


def parse_money(value: str) -> Decimal:
    text = value.strip().replace("R$", "").replace(" ", "")
    if not text:
        raise ValueError("Valor vazio")

    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")

    try:
        return as_decimal(Decimal(text))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Valor monetário inválido") from exc


def format_money(value: Decimal | int | float | str) -> str:
    amount = as_decimal(value)
    formatted = f"{amount:,.2f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def parse_date_ui(value: str, field_name: str = "data", allow_empty: bool = False) -> str | None:
    text = value.strip()
    if not text and allow_empty:
        return None
    if not text:
        raise ValueError(f"Informe {field_name} no formato DD/MM/AAAA.")
    try:
        parsed = datetime.strptime(text, DATE_FMT_UI).date()
    except ValueError as exc:
        raise ValueError(f"{field_name.capitalize()} inválida. Use DD/MM/AAAA.") from exc
    return parsed.strftime(DATE_FMT_DB)


def format_date_ui(value: str | None) -> str:
    if not value:
        return ""
    try:
        return datetime.strptime(value[:10], DATE_FMT_DB).strftime(DATE_FMT_UI)
    except ValueError:
        return value
