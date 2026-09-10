import unittest
from datetime import date
from decimal import Decimal

from core.cnpj import validate_cnpj
from core.dates import add_months
from core.finance import from_cents, split_installments, split_installments_cents, to_cents
from core.formatters import format_money, parse_money
from core.security import hash_password, validate_new_password, verify_password
from tests.fixtures import build_valid_numeric_cnpj


class CoreTests(unittest.TestCase):
    def test_money_ptbr_uses_decimal(self):
        self.assertEqual(parse_money('R$ 1.234,56'), Decimal('1234.56'))
        self.assertEqual(format_money(Decimal('1234.56')), 'R$ 1.234,56')
        self.assertEqual(to_cents(0.1 + 0.2), 30)
        self.assertEqual(from_cents(123456), Decimal('1234.56'))

    def test_installments_keep_exact_cents(self):
        values = split_installments(Decimal('100.00'), 3)
        self.assertEqual(values, [Decimal('33.34'), Decimal('33.33'), Decimal('33.33')])
        self.assertEqual(sum(values), Decimal('100.00'))
        self.assertEqual(split_installments_cents(10000, 3), [3334, 3333, 3333])

    def test_add_months_clamps_last_day(self):
        self.assertEqual(add_months(date(2026, 1, 31), 1), date(2026, 2, 28))

    def test_password_hash(self):
        digest, salt = hash_password('segredo-forte')
        self.assertTrue(verify_password('segredo-forte', digest, salt))
        self.assertFalse(verify_password('errada', digest, salt))

    def test_password_policy(self):
        validate_new_password('MinhaSenha2026')
        with self.assertRaises(ValueError):
            validate_new_password('admin123')
        with self.assertRaises(ValueError):
            validate_new_password('123')

    def test_cnpj_validation(self):
        self.assertTrue(validate_cnpj(build_valid_numeric_cnpj()))
        self.assertFalse(validate_cnpj('11.111.111/1111-11'))


if __name__ == '__main__':
    unittest.main()
