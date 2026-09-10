import sqlite3


class SchemaMixin:
    def create_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT NOT NULL UNIQUE,
                    senha_hash BLOB NOT NULL,
                    salt BLOB NOT NULL,
                    criado_em TEXT NOT NULL,
                    must_change_password INTEGER NOT NULL DEFAULT 0 CHECK (must_change_password IN (0, 1)),
                    ultimo_login_em TEXT
                );

                CREATE TABLE IF NOT EXISTS empresas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    cnpj TEXT,
                    razao_social TEXT,
                    nome_fantasia TEXT,
                    situacao_cadastral TEXT,
                    municipio TEXT,
                    uf TEXT,
                    logradouro TEXT,
                    numero_endereco TEXT,
                    complemento TEXT,
                    bairro TEXT,
                    cep TEXT,
                    telefone TEXT,
                    email TEXT,
                    natureza_juridica TEXT,
                    fonte_cadastral TEXT,
                    consultado_em TEXT,
                    criado_em TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS compras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    empresa_id INTEGER NOT NULL,
                    numero_nota_fiscal TEXT NOT NULL,
                    numero_boleto TEXT NOT NULL,
                    quantidade_boletos INTEGER NOT NULL CHECK (quantidade_boletos > 0),
                    valor_nota_fiscal REAL NOT NULL CHECK (valor_nota_fiscal >= 0),
                    valor_parte_especial REAL NOT NULL CHECK (valor_parte_especial >= 0),
                    valor_total REAL NOT NULL CHECK (valor_total >= 0),
                    valor_nota_fiscal_centavos INTEGER,
                    valor_parte_especial_centavos INTEGER,
                    valor_total_centavos INTEGER,
                    tipo_movimentacao TEXT NOT NULL DEFAULT 'Despesa',
                    centro_custo TEXT NOT NULL DEFAULT 'Administrativo',
                    data_lancamento TEXT,
                    primeiro_vencimento TEXT,
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT,
                    FOREIGN KEY (empresa_id) REFERENCES empresas(id)
                        ON UPDATE CASCADE
                        ON DELETE RESTRICT
                );

                CREATE TABLE IF NOT EXISTS boletos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    compra_id INTEGER NOT NULL,
                    parcela INTEGER NOT NULL CHECK (parcela > 0),
                    numero_boleto TEXT NOT NULL,
                    vencimento TEXT NOT NULL,
                    valor REAL NOT NULL CHECK (valor >= 0),
                    valor_centavos INTEGER,
                    pago INTEGER NOT NULL DEFAULT 0 CHECK (pago IN (0, 1)),
                    data_pagamento TEXT,
                    criado_em TEXT NOT NULL,
                    FOREIGN KEY (compra_id) REFERENCES compras(id)
                        ON UPDATE CASCADE
                        ON DELETE CASCADE,
                    UNIQUE (compra_id, parcela)
                );

                CREATE TABLE IF NOT EXISTS analises_boleto (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    compra_id INTEGER,
                    boleto_id INTEGER,
                    empresa_id INTEGER,
                    empresa_nome TEXT NOT NULL,
                    documento_esperado TEXT,
                    linha_digitavel TEXT NOT NULL,
                    banco_codigo TEXT,
                    valor_codificado REAL,
                    valor_esperado REAL,
                    valor_codificado_centavos INTEGER,
                    valor_esperado_centavos INTEGER,
                    beneficiario_exibido TEXT,
                    documento_exibido TEXT,
                    risco INTEGER NOT NULL,
                    nivel TEXT NOT NULL,
                    motivos_json TEXT NOT NULL,
                    criado_em TEXT NOT NULL,
                    FOREIGN KEY (compra_id) REFERENCES compras(id) ON DELETE SET NULL,
                    FOREIGN KEY (boleto_id) REFERENCES boletos(id) ON DELETE SET NULL,
                    FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS consultas_cnpj (
                    cnpj TEXT PRIMARY KEY,
                    resultado_json TEXT NOT NULL,
                    fonte TEXT,
                    consultado_em TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS auditoria (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ator TEXT NOT NULL,
                    acao TEXT NOT NULL,
                    entidade_tipo TEXT NOT NULL,
                    entidade_id TEXT,
                    detalhes_json TEXT NOT NULL DEFAULT '{}',
                    criado_em TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_consultas_cnpj_data ON consultas_cnpj(consultado_em);
                CREATE INDEX IF NOT EXISTS idx_analises_linha ON analises_boleto(linha_digitavel);
                CREATE INDEX IF NOT EXISTS idx_analises_empresa ON analises_boleto(empresa_id);
                CREATE INDEX IF NOT EXISTS idx_analises_boleto ON analises_boleto(boleto_id);
                CREATE INDEX IF NOT EXISTS idx_compras_empresa ON compras(empresa_id);
                CREATE INDEX IF NOT EXISTS idx_compras_nota ON compras(numero_nota_fiscal);
                CREATE INDEX IF NOT EXISTS idx_compras_boleto ON compras(numero_boleto);
                CREATE INDEX IF NOT EXISTS idx_boletos_compra ON boletos(compra_id);
                CREATE INDEX IF NOT EXISTS idx_boletos_vencimento ON boletos(vencimento);
                CREATE INDEX IF NOT EXISTS idx_boletos_pago ON boletos(pago);
                CREATE INDEX IF NOT EXISTS idx_auditoria_data ON auditoria(criado_em);
                CREATE INDEX IF NOT EXISTS idx_auditoria_acao ON auditoria(acao);
                """
            )

    def _column_names(self, conn: sqlite3.Connection, table: str) -> set[str]:
        return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}

    def _add_missing_columns(self, conn: sqlite3.Connection, table: str, additions: dict[str, str]) -> None:
        cols = self._column_names(conn, table)
        for name, sql_type in additions.items():
            if name not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")

    def migrate_schema(self) -> None:
        """Migração aditiva: preserva bancos V10/V11 e passa a manter centavos inteiros."""
        with self.connect() as conn:
            # Segurança de migração: bancos antigos não possuíam os campos de
            # controle de senha. Quando o campo ainda não existe, todos os usuários
            # legados são marcados para troca obrigatória sem depender de conhecer
            # ou codificar qualquer senha antiga no código-fonte.
            user_columns = self._column_names(conn, "usuarios")
            if "must_change_password" not in user_columns:
                conn.execute(
                    "ALTER TABLE usuarios ADD COLUMN must_change_password "
                    "INTEGER NOT NULL DEFAULT 0"
                )
                conn.execute("UPDATE usuarios SET must_change_password = 1")

            if "ultimo_login_em" not in user_columns:
                conn.execute("ALTER TABLE usuarios ADD COLUMN ultimo_login_em TEXT")

            self._add_missing_columns(conn, "compras", {
                "tipo_movimentacao": "TEXT NOT NULL DEFAULT 'Despesa'",
                "centro_custo": "TEXT NOT NULL DEFAULT 'Administrativo'",
                "data_lancamento": "TEXT",
                "primeiro_vencimento": "TEXT",
                "atualizado_em": "TEXT",
                "valor_nota_fiscal_centavos": "INTEGER",
                "valor_parte_especial_centavos": "INTEGER",
                "valor_total_centavos": "INTEGER",
            })

            self._add_missing_columns(conn, "empresas", {
                "razao_social": "TEXT",
                "nome_fantasia": "TEXT",
                "situacao_cadastral": "TEXT",
                "municipio": "TEXT",
                "uf": "TEXT",
                "logradouro": "TEXT",
                "numero_endereco": "TEXT",
                "complemento": "TEXT",
                "bairro": "TEXT",
                "cep": "TEXT",
                "telefone": "TEXT",
                "email": "TEXT",
                "natureza_juridica": "TEXT",
                "fonte_cadastral": "TEXT",
                "consultado_em": "TEXT",
            })

            self._add_missing_columns(conn, "boletos", {
                "valor_centavos": "INTEGER",
            })

            self._add_missing_columns(conn, "analises_boleto", {
                "valor_codificado_centavos": "INTEGER",
                "valor_esperado_centavos": "INTEGER",
            })

            # Converte uma única vez os valores legados REAL para centavos inteiros.
            conn.execute(
                """
                UPDATE compras
                   SET valor_nota_fiscal_centavos = CAST(ROUND(valor_nota_fiscal * 100) AS INTEGER)
                 WHERE valor_nota_fiscal_centavos IS NULL
                """
            )
            conn.execute(
                """
                UPDATE compras
                   SET valor_parte_especial_centavos = CAST(ROUND(valor_parte_especial * 100) AS INTEGER)
                 WHERE valor_parte_especial_centavos IS NULL
                """
            )
            conn.execute(
                """
                UPDATE compras
                   SET valor_total_centavos = CAST(ROUND(valor_total * 100) AS INTEGER)
                 WHERE valor_total_centavos IS NULL
                """
            )
            conn.execute(
                "UPDATE boletos SET valor_centavos = CAST(ROUND(valor * 100) AS INTEGER) WHERE valor_centavos IS NULL"
            )
            conn.execute(
                "UPDATE analises_boleto SET valor_codificado_centavos = CAST(ROUND(valor_codificado * 100) AS INTEGER) WHERE valor_codificado IS NOT NULL AND valor_codificado_centavos IS NULL"
            )
            conn.execute(
                "UPDATE analises_boleto SET valor_esperado_centavos = CAST(ROUND(valor_esperado * 100) AS INTEGER) WHERE valor_esperado IS NOT NULL AND valor_esperado_centavos IS NULL"
            )

            conn.execute(
                """
                UPDATE compras
                   SET data_lancamento = substr(criado_em, 1, 10)
                 WHERE data_lancamento IS NULL OR data_lancamento = ''
                """
            )
            conn.execute(
                """
                UPDATE compras
                   SET tipo_movimentacao = 'Despesa'
                 WHERE tipo_movimentacao IS NULL OR tipo_movimentacao = ''
                """
            )

            conn.execute("CREATE INDEX IF NOT EXISTS idx_empresas_cnpj ON empresas(cnpj)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_empresas_razao ON empresas(razao_social)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_compras_data ON compras(data_lancamento)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_compras_tipo ON compras(tipo_movimentacao)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_compras_centro_custo ON compras(centro_custo)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_auditoria_data ON auditoria(criado_em)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_auditoria_acao ON auditoria(acao)")
