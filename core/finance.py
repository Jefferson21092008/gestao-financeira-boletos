from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")
HUNDRED = Decimal("100")


def as_decimal(value: Decimal | int | float | str) -> Decimal:
    """Converte valor monetário sem herdar imprecisão binária de float."""
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, float):
        result = Decimal(str(value))
    else:
        result = Decimal(value)
    return result.quantize(CENT, rounding=ROUND_HALF_UP)


def to_cents(value: Decimal | int | float | str) -> int:
    return int((as_decimal(value) * HUNDRED).to_integral_value(rounding=ROUND_HALF_UP))


def from_cents(cents: int | None) -> Decimal:
    return (Decimal(int(cents or 0)) / HUNDRED).quantize(CENT)


def split_installments_cents(total_cents: int, quantity: int) -> list[int]:
    """Divide centavos inteiros sem perda e mantém a soma exata."""
    if quantity <= 0:
        raise ValueError("A quantidade de parcelas deve ser maior que zero.")
    if total_cents < 0:
        raise ValueError("O valor total não pode ser negativo.")
    base, remainder = divmod(int(total_cents), int(quantity))
    return [base + (1 if i < remainder else 0) for i in range(quantity)]


def split_installments(total: Decimal | int | float | str, quantity: int) -> list[Decimal]:
    return [from_cents(cents) for cents in split_installments_cents(to_cents(total), quantity)]
