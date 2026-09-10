import sqlite3
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from core.security import hash_password
from database.database import Database
from tests.fixtures import TEST_DOCUMENT, TEST_PAYMENT_CODE


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / 'teste.db'
        self.db = Database(self.db_path)

    def tearDown(self):
        self.temp.cleanup()

    def test_new_database_has_no_default_password(self):
        self.assertFalse(self.db.has_users())
        self.assertFalse(self.db.authenticate('admin', 'senha-inexistente'))
        self.db.create_initial_admin('SenhaLocal2026')
        self.assertTrue(self.db.authenticate('admin', 'SenhaLocal2026'))
        self.assertFalse(self.db.authenticate('admin', 'senha-inexistente'))

    def test_purchase_generates_exact_installments_and_audit(self):
        self.db.create_initial_admin('SenhaLocal2026')
        company_id = self.db.get_or_create_company('Fornecedor Teste', TEST_DOCUMENT)
        purchase_id = self.db.insert_purchase({
            'empresa_id': company_id,
            'empresa': 'Fornecedor Teste',
            'tipo_movimentacao': 'Despesa',
            'centro_custo': 'Administrativo',
            'data_lancamento': '2026-09-09',
            'numero_nota_fiscal': 'NF-001',
            'numero_boleto': 'BOL-001',
            'quantidade_boletos': 3,
            'primeiro_vencimento': '2026-09-10',
            'valor_nota_fiscal': Decimal('100.00'),
            'valor_parte_especial': Decimal('0.00'),
            'valor_total': Decimal('100.00'),
        })

        purchase = self.db.get_purchase(purchase_id)
        self.assertEqual(purchase['valor_total_centavos'], 10000)
        bills = self.db.list_bills(purchase_id)
        self.assertEqual(len(bills), 3)
        self.assertEqual([row['vencimento'] for row in bills], [
            '2026-09-10', '2026-10-10', '2026-11-10'
        ])
        self.assertEqual([row['valor_centavos'] for row in bills], [3334, 3333, 3333])
        self.assertEqual(sum(row['valor_centavos'] for row in bills), 10000)

        actions = [row['acao'] for row in self.db.list_audit_events()]
        self.assertIn('lancamento_criado', actions)
        self.assertIn('empresa_criada', actions)

    def test_bill_changes_are_audited(self):
        self.db.create_initial_admin('SenhaLocal2026')
        company_id = self.db.get_or_create_company('Fornecedor Teste', TEST_DOCUMENT)
        purchase_id = self.db.insert_purchase({
            'empresa_id': company_id,
            'empresa': 'Fornecedor Teste',
            'tipo_movimentacao': 'Despesa',
            'centro_custo': 'Administrativo',
            'data_lancamento': '2026-09-09',
            'numero_nota_fiscal': 'NF-002',
            'numero_boleto': 'BOL-002',
            'quantidade_boletos': 1,
            'primeiro_vencimento': '2026-09-10',
            'valor_nota_fiscal': Decimal('50.00'),
            'valor_parte_especial': Decimal('0.00'),
            'valor_total': Decimal('50.00'),
        })
        bill_id = self.db.list_bills(purchase_id)[0]['id']
        self.db.set_bill_paid(bill_id, True, '2026-09-09')
        self.db.update_bill_due_date(bill_id, '2026-09-15')
        actions = [row['acao'] for row in self.db.list_audit_events()]
        self.assertIn('boleto_pago', actions)
        self.assertIn('vencimento_boleto_alterado', actions)


    def test_update_purchase_preserves_paid_installment(self):
        self.db.create_initial_admin('SenhaLocal2026')
        company_id = self.db.get_or_create_company('Fornecedor Teste', TEST_DOCUMENT)
        data = {
            'empresa_id': company_id, 'empresa': 'Fornecedor Teste',
            'tipo_movimentacao': 'Despesa', 'centro_custo': 'Administrativo',
            'data_lancamento': '2026-09-09', 'numero_nota_fiscal': 'NF-003',
            'numero_boleto': 'BOL-003', 'quantidade_boletos': 2,
            'primeiro_vencimento': '2026-09-10',
            'valor_nota_fiscal': Decimal('20.00'), 'valor_parte_especial': Decimal('0.00'),
            'valor_total': Decimal('20.00'),
        }
        purchase_id = self.db.insert_purchase(data)
        first_bill = self.db.list_bills(purchase_id)[0]
        self.db.set_bill_paid(first_bill['id'], True, '2026-09-09')
        data['valor_nota_fiscal'] = Decimal('20.01')
        data['valor_total'] = Decimal('20.01')
        self.db.update_purchase(purchase_id, data)
        bills = self.db.list_bills(purchase_id)
        self.assertEqual([b['valor_centavos'] for b in bills], [1001, 1000])
        self.assertEqual(bills[0]['pago'], 1)
        self.assertEqual(bills[0]['data_pagamento'], '2026-09-09')

    def test_fraud_analysis_is_saved_in_cents_and_audited(self):
        self.db.create_initial_admin('SenhaLocal2026')
        analysis_id = self.db.save_boleto_analysis(
            compra_id=None, boleto_id=None, empresa_id=None, empresa_nome='Fornecedor',
            documento_esperado=TEST_DOCUMENT, linha_digitavel=TEST_PAYMENT_CODE,
            banco_codigo='001', valor_codificado=Decimal('10.01'), valor_esperado=Decimal('10.01'),
            beneficiario_exibido='Fornecedor', documento_exibido=TEST_DOCUMENT,
            risk={'score': 0, 'level': 'BAIXO', 'reasons': []},
        )
        with self.db.connect() as conn:
            row = conn.execute('SELECT valor_codificado_centavos, valor_esperado_centavos FROM analises_boleto WHERE id = ?', (analysis_id,)).fetchone()
        self.assertEqual(row['valor_codificado_centavos'], 1001)
        self.assertEqual(row['valor_esperado_centavos'], 1001)
        self.assertIn('boleto_analisado', [r['acao'] for r in self.db.list_audit_events()])

    def test_schema_contains_v12_tables_and_columns(self):
        with self.db.connect() as conn:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            purchase_cols = {r['name'] for r in conn.execute('PRAGMA table_info(compras)')}
            bill_cols = {r['name'] for r in conn.execute('PRAGMA table_info(boletos)')}
        self.assertTrue({'usuarios', 'empresas', 'compras', 'boletos', 'analises_boleto', 'consultas_cnpj', 'auditoria'} <= tables)
        self.assertIn('valor_total_centavos', purchase_cols)
        self.assertIn('valor_centavos', bill_cols)

    def test_connection_closes_after_context(self):
        conn = self.db.connect()
        with conn:
            conn.execute('SELECT 1').fetchone()
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute('SELECT 1')


class CompatibilityAndBackupTests(unittest.TestCase):
    def test_old_schema_is_migrated_without_losing_data_and_money_is_backfilled(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / 'antigo.db'
            conn = sqlite3.connect(db_path)
            try:
                conn.executescript('''
                    CREATE TABLE usuarios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        usuario TEXT NOT NULL UNIQUE,
                        senha_hash BLOB NOT NULL,
                        salt BLOB NOT NULL,
                        criado_em TEXT NOT NULL
                    );
                    CREATE TABLE empresas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome TEXT NOT NULL COLLATE NOCASE UNIQUE,
                        cnpj TEXT,
                        criado_em TEXT NOT NULL
                    );
                    CREATE TABLE compras (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        empresa_id INTEGER NOT NULL,
                        numero_nota_fiscal TEXT NOT NULL,
                        numero_boleto TEXT NOT NULL,
                        quantidade_boletos INTEGER NOT NULL,
                        valor_nota_fiscal REAL NOT NULL,
                        valor_parte_especial REAL NOT NULL,
                        valor_total REAL NOT NULL,
                        criado_em TEXT NOT NULL,
                        FOREIGN KEY (empresa_id) REFERENCES empresas(id)
                    );
                    CREATE TABLE boletos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        compra_id INTEGER NOT NULL,
                        parcela INTEGER NOT NULL,
                        numero_boleto TEXT NOT NULL,
                        vencimento TEXT NOT NULL,
                        valor REAL NOT NULL,
                        pago INTEGER NOT NULL DEFAULT 0,
                        data_pagamento TEXT,
                        criado_em TEXT NOT NULL,
                        FOREIGN KEY (compra_id) REFERENCES compras(id) ON DELETE CASCADE,
                        UNIQUE (compra_id, parcela)
                    );
                    CREATE TABLE analises_boleto (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        compra_id INTEGER, boleto_id INTEGER, empresa_id INTEGER,
                        empresa_nome TEXT NOT NULL, documento_esperado TEXT,
                        linha_digitavel TEXT NOT NULL, banco_codigo TEXT,
                        valor_codificado REAL, valor_esperado REAL,
                        beneficiario_exibido TEXT, documento_exibido TEXT,
                        risco INTEGER NOT NULL, nivel TEXT NOT NULL,
                        motivos_json TEXT NOT NULL, criado_em TEXT NOT NULL
                    );
                    CREATE TABLE consultas_cnpj (
                        cnpj TEXT PRIMARY KEY, resultado_json TEXT NOT NULL,
                        fonte TEXT, consultado_em TEXT NOT NULL
                    );
                ''')
                digest, salt = hash_password('SenhaLegadaSegura2025')
                conn.execute("INSERT INTO usuarios(usuario, senha_hash, salt, criado_em) VALUES(?, ?, ?, ?)", ('admin', digest, salt, '2025-01-01 09:00:00'))
                conn.execute("INSERT INTO empresas(nome, cnpj, criado_em) VALUES('Empresa Antiga', '', '2025-01-01 10:00:00')")
                conn.execute("INSERT INTO compras(empresa_id, numero_nota_fiscal, numero_boleto, quantidade_boletos, valor_nota_fiscal, valor_parte_especial, valor_total, criado_em) VALUES(1, 'NF', 'B', 1, 10.01, 0, 10.01, '2025-01-02 10:00:00')")
                conn.execute("INSERT INTO boletos(compra_id, parcela, numero_boleto, vencimento, valor, pago, criado_em) VALUES(1,1,'B','2025-02-01',10.01,0,'2025-01-02 10:00:00')")
                conn.commit()
            finally:
                conn.close()

            db = Database(db_path)
            row = db.get_purchase(1)
            self.assertIsNotNone(row)
            self.assertEqual(row['empresa'], 'Empresa Antiga')
            self.assertEqual(row['tipo_movimentacao'], 'Despesa')
            self.assertEqual(row['data_lancamento'], '2025-01-02')
            self.assertEqual(row['valor_total_centavos'], 1001)
            self.assertEqual(db.list_bills(1)[0]['valor_centavos'], 1001)
            self.assertTrue(db.user_requires_password_change('admin'))
            self.assertTrue(db.authenticate('admin', 'SenhaLegadaSegura2025'))
            db.force_change_password('admin', 'SenhaNova2026')
            self.assertTrue(db.authenticate('admin', 'SenhaNova2026'))
            self.assertFalse(db.user_requires_password_change('admin'))

    def test_backup_and_restore_roundtrip(self):
        import repositories.backup_repository as backup_module
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            old_backup_dir = backup_module.BACKUP_DIR
            backup_module.BACKUP_DIR = tmp_path / 'backups'
            try:
                db = Database(tmp_path / 'dados.db')
                db.create_initial_admin('SenhaLocal2026')
                db.get_or_create_company('Antes', '')
                backup = db.create_backup('teste')
                db.get_or_create_company('Depois', '')
                self.assertEqual(len(db.list_companies()), 2)
                db.restore_backup(backup)
                names = [r['nome'] for r in db.list_companies()]
                self.assertEqual(names, ['Antes'])
                self.assertIn('backup_restaurado', [r['acao'] for r in db.list_audit_events()])
            finally:
                backup_module.BACKUP_DIR = old_backup_dir


    def test_export_external_backup_is_valid_and_audited(self):
        import repositories.backup_repository as backup_module
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            old_backup_dir = backup_module.BACKUP_DIR
            backup_module.BACKUP_DIR = tmp_path / 'backups'
            try:
                db = Database(tmp_path / 'dados.db')
                db.create_initial_admin('SenhaLocal2026')
                db.get_or_create_company('Empresa Backup', '')
                destination = tmp_path / 'externo' / 'copia_empresa.db'
                exported = db.export_backup(destination)
                self.assertEqual(exported, destination)
                self.assertTrue(destination.exists())
                db.validate_backup_file(destination)
                actions = [r['acao'] for r in db.list_audit_events()]
                self.assertIn('backup_exportado', actions)
            finally:
                backup_module.BACKUP_DIR = old_backup_dir


if __name__ == '__main__':
    unittest.main()
