import unittest
from decimal import Decimal

from services.fraud_service import calculate_fraud_risk, inspect_payment_code
from tests.fixtures import TEST_DOCUMENT


class FraudTests(unittest.TestCase):
    def test_invalid_payment_code_is_high_risk(self):
        inspection = inspect_payment_code('123')
        result = calculate_fraud_risk(
            inspection=inspection,
            expected_name='Fornecedor Teste',
            expected_doc=TEST_DOCUMENT,
            shown_name='Fornecedor Teste',
            shown_doc=TEST_DOCUMENT,
            expected_value=Decimal('100.00'),
        )
        self.assertEqual(result['level'], 'ALTO')
        self.assertGreaterEqual(result['score'], 50)

    def test_missing_confirmation_data_never_returns_low(self):
        inspection = {
            'valid_structure': True,
            'checks_ok': True,
            'encoded_value': Decimal('100.00'),
            'details': [],
        }
        result = calculate_fraud_risk(
            inspection=inspection,
            expected_name='Fornecedor Teste',
            expected_doc=TEST_DOCUMENT,
            shown_name='',
            shown_doc='',
            expected_value=Decimal('100.00'),
        )
        self.assertEqual(result['level'], 'ATENÇÃO')

    def test_fully_matching_data_can_be_low_risk(self):
        inspection = {
            'valid_structure': True,
            'checks_ok': True,
            'encoded_value': Decimal('100.00'),
            'details': [],
        }
        result = calculate_fraud_risk(
            inspection=inspection,
            expected_name='Fornecedor Teste LTDA',
            expected_doc=TEST_DOCUMENT,
            shown_name='Fornecedor Teste LTDA',
            shown_doc=TEST_DOCUMENT,
            expected_value=Decimal('100.00'),
            cnpj_lookup={
                'status': 'ok', 'situacao': 'ATIVA',
                'razao_social': 'Fornecedor Teste LTDA', 'nome_fantasia': '',
            },
        )
        self.assertEqual(result['level'], 'BAIXO')
        self.assertEqual(result['score'], 0)

    def test_duplicate_other_company_is_high_risk(self):
        inspection = {'valid_structure': True, 'checks_ok': True, 'encoded_value': Decimal('100.00'), 'details': []}
        result = calculate_fraud_risk(
            inspection=inspection,
            expected_name='Fornecedor Teste',
            expected_doc=TEST_DOCUMENT,
            shown_name='Fornecedor Teste',
            shown_doc=TEST_DOCUMENT,
            expected_value=Decimal('100.00'),
            duplicate_other_company=True,
        )
        self.assertEqual(result['level'], 'ALTO')

    def test_previous_high_risk_for_same_line_requires_attention(self):
        inspection = {'valid_structure': True, 'checks_ok': True, 'encoded_value': Decimal('100.00'), 'details': []}
        result = calculate_fraud_risk(
            inspection=inspection,
            expected_name='Fornecedor Teste',
            expected_doc=TEST_DOCUMENT,
            shown_name='Fornecedor Teste',
            shown_doc=TEST_DOCUMENT,
            expected_value=Decimal('100.00'),
            prior_high_risk_same_line=True,
        )
        self.assertEqual(result['level'], 'ATENÇÃO')


if __name__ == '__main__':
    unittest.main()
