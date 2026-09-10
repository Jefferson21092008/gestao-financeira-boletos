import json
import sqlite3
from datetime import datetime, timedelta

from config import CNPJ_CACHE_HOURS
from core.cnpj import cnpj_compact
from core.dates import now_iso
from core.finance import from_cents, to_cents
from core.text import digits_only
from services.cnpj_service import query_cnpj_brasilapi


class FraudRepositoryMixin:
    def get_bill_context(self, bill_id: int) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT b.id AS boleto_id, b.compra_id, b.numero_boleto, b.parcela, b.valor,
                       b.valor_centavos, b.vencimento, e.id AS empresa_id, e.nome AS empresa,
                       COALESCE(e.cnpj, '') AS cnpj, c.numero_nota_fiscal
                  FROM boletos b
                  JOIN compras c ON c.id = b.compra_id
                  JOIN empresas e ON e.id = c.empresa_id
                 WHERE b.id = ?
                """,
                (int(bill_id),),
            ).fetchone()

    def boleto_duplicate_other_company(self, line: str, empresa_id: int | None) -> bool:
        clean = digits_only(line)
        if not clean:
            return False
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT 1 FROM analises_boleto
                 WHERE linha_digitavel = ?
                   AND empresa_id IS NOT NULL
                   AND (? IS NULL OR empresa_id <> ?)
                 LIMIT 1
                """,
                (clean, empresa_id, empresa_id),
            ).fetchone()
        return row is not None

    def boleto_prior_high_risk(self, line: str) -> bool:
        clean = digits_only(line)
        if not clean:
            return False
        with self.connect() as conn:
            return conn.execute(
                "SELECT 1 FROM analises_boleto WHERE linha_digitavel = ? AND risco >= 50 LIMIT 1",
                (clean,),
            ).fetchone() is not None

    def boleto_unusual_bank(self, empresa_id: int | None, bank_code: str) -> bool:
        """Usa apenas análises anteriores de baixo risco como histórico de confiança."""
        if not empresa_id or not bank_code:
            return False
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT banco_codigo, COUNT(*) AS qtd
                  FROM analises_boleto
                 WHERE empresa_id = ?
                   AND nivel = 'BAIXO'
                   AND COALESCE(banco_codigo, '') <> ''
                 GROUP BY banco_codigo
                """,
                (int(empresa_id),),
            ).fetchall()
        total = sum(int(r["qtd"]) for r in rows)
        seen = {r["banco_codigo"] for r in rows}
        return total >= 3 and bank_code not in seen

    def get_cnpj_cache(self, cnpj: str, max_age_hours: int = CNPJ_CACHE_HOURS) -> dict | None:
        d = cnpj_compact(cnpj)
        if len(d) != 14:
            return None
        with self.connect() as conn:
            row = conn.execute(
                "SELECT resultado_json, consultado_em FROM consultas_cnpj WHERE cnpj = ?",
                (d,),
            ).fetchone()
        if not row:
            return None
        try:
            when = datetime.strptime(row["consultado_em"], "%Y-%m-%d %H:%M:%S")
            if datetime.now() - when > timedelta(hours=max_age_hours):
                return None
            data = json.loads(row["resultado_json"])
            data["cached"] = True
            return data
        except (ValueError, TypeError, json.JSONDecodeError):
            return None

    def save_cnpj_cache(self, cnpj: str, result: dict) -> None:
        d = cnpj_compact(cnpj)
        if len(d) != 14 or result.get("status") not in {"ok", "not_found"}:
            return
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO consultas_cnpj (cnpj, resultado_json, fonte, consultado_em)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(cnpj) DO UPDATE SET
                    resultado_json = excluded.resultado_json,
                    fonte = excluded.fonte,
                    consultado_em = excluded.consultado_em
                """,
                (d, json.dumps(result, ensure_ascii=False), result.get("source", ""), now_iso()),
            )

    def lookup_cnpj(self, cnpj: str, *, force_refresh: bool = False) -> dict:
        if not force_refresh:
            cached = self.get_cnpj_cache(cnpj)
            if cached:
                return cached
        result = query_cnpj_brasilapi(cnpj)
        self.save_cnpj_cache(cnpj, result)
        return result

    def save_boleto_analysis(
        self,
        *,
        compra_id: int | None,
        boleto_id: int | None,
        empresa_id: int | None,
        empresa_nome: str,
        documento_esperado: str,
        linha_digitavel: str,
        banco_codigo: str,
        valor_codificado,
        valor_esperado,
        beneficiario_exibido: str,
        documento_exibido: str,
        risk: dict,
    ) -> int:
        encoded_cents = None if valor_codificado is None else to_cents(valor_codificado)
        expected_cents = None if valor_esperado is None else to_cents(valor_esperado)
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO analises_boleto (
                    compra_id, boleto_id, empresa_id, empresa_nome, documento_esperado,
                    linha_digitavel, banco_codigo, valor_codificado, valor_esperado,
                    valor_codificado_centavos, valor_esperado_centavos,
                    beneficiario_exibido, documento_exibido, risco, nivel, motivos_json, criado_em
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    compra_id,
                    boleto_id,
                    empresa_id,
                    empresa_nome.strip(),
                    documento_esperado.strip(),
                    digits_only(linha_digitavel),
                    banco_codigo,
                    None if encoded_cents is None else float(from_cents(encoded_cents)),
                    None if expected_cents is None else float(from_cents(expected_cents)),
                    encoded_cents,
                    expected_cents,
                    beneficiario_exibido.strip(),
                    documento_exibido.strip(),
                    int(risk["score"]),
                    risk["level"],
                    json.dumps(risk["reasons"], ensure_ascii=False),
                    now_iso(),
                ),
            )
            analysis_id = int(cur.lastrowid)
            self.audit_event(
                "boleto_analisado",
                entity_type="analise_boleto",
                entity_id=analysis_id,
                details={
                    "boleto_id": boleto_id,
                    "compra_id": compra_id,
                    "empresa_id": empresa_id,
                    "risco": int(risk["score"]),
                    "nivel": risk["level"],
                    "banco_codigo": banco_codigo,
                },
                conn=conn,
            )
            return analysis_id

    def list_boleto_analyses(self, limit: int = 20) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT id, empresa_nome, linha_digitavel, banco_codigo, valor_esperado,
                       valor_esperado_centavos, risco, nivel, criado_em
                  FROM analises_boleto
                 ORDER BY id DESC
                 LIMIT ?
                """,
                (int(limit),),
            ).fetchall()

    def latest_bill_analysis(self, bill_id: int) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT id, risco, nivel, criado_em
                  FROM analises_boleto
                 WHERE boleto_id = ?
                 ORDER BY id DESC
                 LIMIT 1
                """,
                (int(bill_id),),
            ).fetchone()
