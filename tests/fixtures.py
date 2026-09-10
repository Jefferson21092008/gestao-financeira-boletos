"""Dados sintéticos usados exclusivamente pela suíte de testes."""

TEST_DOCUMENT = "00.000.000/0000-00"
TEST_PAYMENT_CODE = "12345678901" * 4  # 44 dígitos sintéticos, sem origem bancária real.


def build_valid_numeric_cnpj(base12: str = "123456780001") -> str:
    """Gera, em tempo de teste, dígitos verificadores válidos para uma base sintética."""
    if len(base12) != 12 or not base12.isdigit():
        raise ValueError("A base de teste deve conter exatamente 12 dígitos.")

    def digit(base: str, weights: tuple[int, ...]) -> str:
        total = sum(int(ch) * weight for ch, weight in zip(base, weights))
        remainder = total % 11
        return "0" if remainder in (0, 1) else str(11 - remainder)

    dv1 = digit(base12, (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))
    dv2 = digit(base12 + dv1, (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))
    return base12 + dv1 + dv2
