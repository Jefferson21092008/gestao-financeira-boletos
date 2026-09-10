import sqlite3
from config import COST_CENTERS
from core.cnpj import cnpj_compact, format_cnpj, validate_cnpj
from core.dates import now_iso


class CompanyRepositoryMixin:
    def get_or_create_company(self, name: str, cnpj: str, conn: sqlite3.Connection | None = None) -> int:
        own_conn = conn is None
        if own_conn:
            conn = self.connect()
        assert conn is not None
        try:
            name = name.strip()
            cnpj = cnpj.strip()
            row = conn.execute(
                "SELECT id, cnpj FROM empresas WHERE nome = ? COLLATE NOCASE", (name,)
            ).fetchone()
            if row:
                if cnpj and cnpj != (row["cnpj"] or ""):
                    conn.execute("UPDATE empresas SET cnpj = ? WHERE id = ?", (cnpj, row["id"]))
                    self.audit_event(
                        "empresa_atualizada", entity_type="empresa", entity_id=int(row["id"]),
                        details={"nome": name, "cnpj": cnpj}, conn=conn,
                    )
                if own_conn:
                    conn.commit()
                return int(row["id"])

            cursor = conn.execute(
                "INSERT INTO empresas (nome, cnpj, criado_em) VALUES (?, ?, ?)",
                (name, cnpj or None, now_iso()),
            )
            company_id = int(cursor.lastrowid)
            self.audit_event(
                "empresa_criada", entity_type="empresa", entity_id=company_id,
                details={"nome": name, "cnpj": cnpj or ""}, conn=conn,
            )
            if own_conn:
                conn.commit()
            return company_id
        finally:
            if own_conn:
                conn.close()

    def list_companies(self, prefix: str = "", limit: int = 100) -> list[sqlite3.Row]:
        """Pesquisa somente empresas já cadastradas no banco local."""
        term = f"%{prefix.strip()}%"
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT id, nome, COALESCE(cnpj, '') AS cnpj,
                       COALESCE(razao_social, '') AS razao_social,
                       COALESCE(nome_fantasia, '') AS nome_fantasia,
                       COALESCE(situacao_cadastral, '') AS situacao_cadastral,
                       COALESCE(municipio, '') AS municipio,
                       COALESCE(uf, '') AS uf,
                       COALESCE(logradouro, '') AS logradouro,
                       COALESCE(numero_endereco, '') AS numero_endereco,
                       COALESCE(complemento, '') AS complemento,
                       COALESCE(bairro, '') AS bairro,
                       COALESCE(cep, '') AS cep,
                       COALESCE(telefone, '') AS telefone,
                       COALESCE(email, '') AS email,
                       COALESCE(natureza_juridica, '') AS natureza_juridica,
                       COALESCE(fonte_cadastral, '') AS fonte_cadastral,
                       COALESCE(consultado_em, '') AS consultado_em,
                       criado_em
                  FROM empresas
                 WHERE (? = '%%'
                        OR nome LIKE ?
                        OR COALESCE(cnpj, '') LIKE ?
                        OR COALESCE(razao_social, '') LIKE ?
                        OR COALESCE(nome_fantasia, '') LIKE ?
                        OR COALESCE(municipio, '') LIKE ?)
                 ORDER BY COALESCE(NULLIF(nome_fantasia, ''), NULLIF(razao_social, ''), nome) COLLATE NOCASE
                 LIMIT ?
                """,
                (term, term, term, term, term, term, int(limit)),
            ).fetchall()

    def get_company(self, company_id: int) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT id, nome, COALESCE(cnpj, '') AS cnpj,
                       COALESCE(razao_social, '') AS razao_social,
                       COALESCE(nome_fantasia, '') AS nome_fantasia,
                       COALESCE(situacao_cadastral, '') AS situacao_cadastral,
                       COALESCE(municipio, '') AS municipio, COALESCE(uf, '') AS uf,
                       COALESCE(logradouro, '') AS logradouro,
                       COALESCE(numero_endereco, '') AS numero_endereco,
                       COALESCE(complemento, '') AS complemento, COALESCE(bairro, '') AS bairro,
                       COALESCE(cep, '') AS cep, COALESCE(telefone, '') AS telefone,
                       COALESCE(email, '') AS email, COALESCE(natureza_juridica, '') AS natureza_juridica,
                       COALESCE(fonte_cadastral, '') AS fonte_cadastral,
                       COALESCE(consultado_em, '') AS consultado_em, criado_em
                  FROM empresas
                 WHERE id = ?
                """,
                (int(company_id),),
            ).fetchone()

    def get_company_by_cnpj(self, cnpj: str) -> sqlite3.Row | None:
        doc = cnpj_compact(cnpj)
        if not doc:
            return None
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT id, nome, COALESCE(cnpj, '') AS cnpj,
                       COALESCE(razao_social, '') AS razao_social,
                       COALESCE(nome_fantasia, '') AS nome_fantasia,
                       COALESCE(situacao_cadastral, '') AS situacao_cadastral,
                       COALESCE(municipio, '') AS municipio, COALESCE(uf, '') AS uf,
                       COALESCE(logradouro, '') AS logradouro,
                       COALESCE(numero_endereco, '') AS numero_endereco,
                       COALESCE(complemento, '') AS complemento,
                       COALESCE(bairro, '') AS bairro, COALESCE(cep, '') AS cep,
                       COALESCE(telefone, '') AS telefone, COALESCE(email, '') AS email,
                       COALESCE(natureza_juridica, '') AS natureza_juridica,
                       COALESCE(fonte_cadastral, '') AS fonte_cadastral,
                       COALESCE(consultado_em, '') AS consultado_em, criado_em
                  FROM empresas
                 WHERE REPLACE(REPLACE(REPLACE(REPLACE(UPPER(COALESCE(cnpj,'')), '.', ''), '/', ''), '-', ''), ' ', '') = ?
                 LIMIT 1
                """,
                (doc,),
            ).fetchone()

    def upsert_company_from_lookup(self, result: dict) -> int:
        """Cadastra/atualiza automaticamente uma empresa a partir da consulta online."""
        if result.get("status") != "ok":
            raise ValueError("A consulta cadastral não retornou uma empresa válida para cadastro.")
        cnpj = cnpj_compact(result.get("cnpj", ""))
        if not validate_cnpj(cnpj):
            raise ValueError("O CNPJ retornado não passou na validação local.")
        razao = (result.get("razao_social") or "").strip()
        fantasia = (result.get("nome_fantasia") or "").strip()
        display = razao or fantasia or format_cnpj(cnpj)
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT id, nome FROM empresas WHERE REPLACE(REPLACE(REPLACE(REPLACE(UPPER(COALESCE(cnpj,'')), '.', ''), '/', ''), '-', ''), ' ', '') = ?",
                (cnpj,),
            ).fetchone()
            if existing:
                company_id = int(existing["id"])
                current_name = existing["nome"] or display
                display_name = razao or current_name
                conflict = conn.execute(
                    "SELECT 1 FROM empresas WHERE nome = ? COLLATE NOCASE AND id <> ?",
                    (display_name, company_id),
                ).fetchone()
                if conflict:
                    display_name = f"{display_name} · {format_cnpj(cnpj)}"
            else:
                display_name = display
                # O campo nome é legado e UNIQUE. Em uma colisão rara de razão social,
                # acrescentamos o CNPJ somente ao identificador visual local.
                conflict = conn.execute("SELECT 1 FROM empresas WHERE nome = ? COLLATE NOCASE", (display_name,)).fetchone()
                if conflict:
                    display_name = f"{display_name} · {format_cnpj(cnpj)}"
                cur = conn.execute(
                    "INSERT INTO empresas (nome, cnpj, criado_em) VALUES (?, ?, ?)",
                    (display_name, format_cnpj(cnpj), now_iso()),
                )
                company_id = int(cur.lastrowid)

            conn.execute(
                """
                UPDATE empresas
                   SET nome = ?, cnpj = ?, razao_social = ?, nome_fantasia = ?,
                       situacao_cadastral = ?, municipio = ?, uf = ?, logradouro = ?,
                       numero_endereco = ?, complemento = ?, bairro = ?, cep = ?,
                       telefone = ?, email = ?, natureza_juridica = ?,
                       fonte_cadastral = ?, consultado_em = ?
                 WHERE id = ?
                """,
                (
                    display_name, format_cnpj(cnpj), razao, fantasia,
                    (result.get("situacao") or "").strip().upper(),
                    (result.get("municipio") or "").strip(), (result.get("uf") or "").strip(),
                    (result.get("logradouro") or "").strip(), (result.get("numero") or "").strip(),
                    (result.get("complemento") or "").strip(), (result.get("bairro") or "").strip(),
                    (result.get("cep") or "").strip(), (result.get("telefone") or "").strip(),
                    (result.get("email") or "").strip(), (result.get("natureza_juridica") or "").strip(),
                    (result.get("source") or "").strip(), now_iso(), company_id,
                ),
            )
            self.audit_event(
                "empresa_consultada_atualizada", entity_type="empresa", entity_id=company_id,
                details={
                    "nome": display_name, "cnpj": format_cnpj(cnpj),
                    "situacao": (result.get("situacao") or "").strip().upper(),
                    "fonte": (result.get("source") or "").strip(),
                }, conn=conn,
            )
        return company_id

    def get_company_for_purchase(self, purchase_id: int) -> sqlite3.Row | None:
        with self.connect() as conn:
            row = conn.execute("SELECT empresa_id FROM compras WHERE id = ?", (purchase_id,)).fetchone()
        return self.get_company(int(row["empresa_id"])) if row else None

    def get_company_exact(self, name: str) -> sqlite3.Row | None:
        query = name.strip()
        if not query:
            return None
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id, nome, COALESCE(cnpj, '') AS cnpj,
                       COALESCE(razao_social, '') AS razao_social,
                       COALESCE(nome_fantasia, '') AS nome_fantasia,
                       COALESCE(situacao_cadastral, '') AS situacao_cadastral,
                       COALESCE(municipio, '') AS municipio, COALESCE(uf, '') AS uf,
                       COALESCE(logradouro, '') AS logradouro,
                       COALESCE(numero_endereco, '') AS numero_endereco,
                       COALESCE(complemento, '') AS complemento, COALESCE(bairro, '') AS bairro,
                       COALESCE(cep, '') AS cep, COALESCE(telefone, '') AS telefone,
                       COALESCE(email, '') AS email, COALESCE(natureza_juridica, '') AS natureza_juridica,
                       COALESCE(fonte_cadastral, '') AS fonte_cadastral,
                       COALESCE(consultado_em, '') AS consultado_em, criado_em
                  FROM empresas
                 WHERE nome = ? COLLATE NOCASE
                    OR razao_social = ? COLLATE NOCASE
                    OR nome_fantasia = ? COLLATE NOCASE
                 ORDER BY CASE
                            WHEN nome = ? COLLATE NOCASE THEN 0
                            WHEN razao_social = ? COLLATE NOCASE THEN 1
                            ELSE 2
                          END, id
                 LIMIT 1
                """,
                (query, query, query, query, query),
            ).fetchone()
        return row
