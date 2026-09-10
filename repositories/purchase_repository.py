import sqlite3
from datetime import date, datetime, timedelta

from config import COST_CENTERS, DATE_FMT_DB
from core.dates import add_months, now_iso, today_db
from core.finance import from_cents, split_installments_cents, to_cents


class PurchaseRepositoryMixin:
    def _resolve_company(self, conn: sqlite3.Connection, data: dict) -> int:
        company_id_hint = data.get("empresa_id")
        if company_id_hint is not None:
            company = conn.execute(
                "SELECT id FROM empresas WHERE id = ?",
                (int(company_id_hint),),
            ).fetchone()
        else:
            company = conn.execute(
                "SELECT id FROM empresas WHERE nome = ? COLLATE NOCASE",
                (data["empresa"].strip(),),
            ).fetchone()
        if not company:
            raise ValueError(
                "Empresa não cadastrada. Cadastre e valide o CNPJ no menu Empresas antes de criar ou atualizar o lançamento."
            )
        return int(company["id"])

    def _money_values(self, data: dict) -> tuple[int, int, int]:
        nf = to_cents(data["valor_nota_fiscal"])
        special = to_cents(data["valor_parte_especial"])
        total = to_cents(data["valor_total"])
        return nf, special, total

    def _sync_bills(self, conn: sqlite3.Connection, purchase_id: int, data: dict) -> None:
        existing = {
            int(row["parcela"]): row
            for row in conn.execute(
                "SELECT * FROM boletos WHERE compra_id = ?", (purchase_id,)
            ).fetchall()
        }

        first_due = datetime.strptime(data["primeiro_vencimento"], DATE_FMT_DB).date()
        total_cents = to_cents(data["valor_total"])
        amounts = split_installments_cents(total_cents, int(data["quantidade_boletos"]))

        for parcel in range(1, int(data["quantidade_boletos"]) + 1):
            due = add_months(first_due, parcel - 1).strftime(DATE_FMT_DB)
            old = existing.get(parcel)
            paid = int(old["pago"]) if old else 0
            payment_date = old["data_pagamento"] if old else None
            cents = amounts[parcel - 1]
            legacy_value = float(from_cents(cents))

            conn.execute(
                """
                INSERT INTO boletos (
                    compra_id, parcela, numero_boleto, vencimento,
                    valor, valor_centavos, pago, data_pagamento, criado_em
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(compra_id, parcela) DO UPDATE SET
                    numero_boleto = excluded.numero_boleto,
                    vencimento = excluded.vencimento,
                    valor = excluded.valor,
                    valor_centavos = excluded.valor_centavos,
                    pago = boletos.pago,
                    data_pagamento = boletos.data_pagamento
                """,
                (
                    purchase_id,
                    parcel,
                    data["numero_boleto"],
                    due,
                    legacy_value,
                    cents,
                    paid,
                    payment_date,
                    now_iso(),
                ),
            )

        conn.execute(
            "DELETE FROM boletos WHERE compra_id = ? AND parcela > ?",
            (purchase_id, int(data["quantidade_boletos"])),
        )

    def insert_purchase(self, data: dict) -> int:
        with self.connect() as conn:
            company_id = self._resolve_company(conn, data)
            nf_cents, special_cents, total_cents = self._money_values(data)
            cursor = conn.execute(
                """
                INSERT INTO compras (
                    empresa_id, tipo_movimentacao, centro_custo, data_lancamento,
                    numero_nota_fiscal, numero_boleto, quantidade_boletos,
                    primeiro_vencimento, valor_nota_fiscal,
                    valor_parte_especial, valor_total,
                    valor_nota_fiscal_centavos, valor_parte_especial_centavos, valor_total_centavos,
                    criado_em, atualizado_em
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company_id,
                    data["tipo_movimentacao"],
                    data["centro_custo"],
                    data["data_lancamento"],
                    data["numero_nota_fiscal"],
                    data["numero_boleto"],
                    int(data["quantidade_boletos"]),
                    data["primeiro_vencimento"],
                    float(from_cents(nf_cents)),
                    float(from_cents(special_cents)),
                    float(from_cents(total_cents)),
                    nf_cents,
                    special_cents,
                    total_cents,
                    now_iso(),
                    now_iso(),
                ),
            )
            purchase_id = int(cursor.lastrowid)
            self._sync_bills(conn, purchase_id, data)
            self.audit_event(
                "lancamento_criado",
                entity_type="lancamento",
                entity_id=purchase_id,
                details={
                    "empresa_id": company_id,
                    "nota": data["numero_nota_fiscal"],
                    "boleto": data["numero_boleto"],
                    "valor_total_centavos": total_cents,
                    "parcelas": int(data["quantidade_boletos"]),
                },
                conn=conn,
            )
            return purchase_id

    def update_purchase(self, purchase_id: int, data: dict) -> None:
        with self.connect() as conn:
            company_id = self._resolve_company(conn, data)
            nf_cents, special_cents, total_cents = self._money_values(data)
            cur = conn.execute(
                """
                UPDATE compras
                   SET empresa_id = ?,
                       tipo_movimentacao = ?,
                       centro_custo = ?,
                       data_lancamento = ?,
                       numero_nota_fiscal = ?,
                       numero_boleto = ?,
                       quantidade_boletos = ?,
                       primeiro_vencimento = ?,
                       valor_nota_fiscal = ?,
                       valor_parte_especial = ?,
                       valor_total = ?,
                       valor_nota_fiscal_centavos = ?,
                       valor_parte_especial_centavos = ?,
                       valor_total_centavos = ?,
                       atualizado_em = ?
                 WHERE id = ?
                """,
                (
                    company_id,
                    data["tipo_movimentacao"],
                    data["centro_custo"],
                    data["data_lancamento"],
                    data["numero_nota_fiscal"],
                    data["numero_boleto"],
                    int(data["quantidade_boletos"]),
                    data["primeiro_vencimento"],
                    float(from_cents(nf_cents)),
                    float(from_cents(special_cents)),
                    float(from_cents(total_cents)),
                    nf_cents,
                    special_cents,
                    total_cents,
                    now_iso(),
                    int(purchase_id),
                ),
            )
            if cur.rowcount == 0:
                raise ValueError("Lançamento não encontrado.")
            self._sync_bills(conn, int(purchase_id), data)
            self.audit_event(
                "lancamento_atualizado",
                entity_type="lancamento",
                entity_id=purchase_id,
                details={
                    "empresa_id": company_id,
                    "nota": data["numero_nota_fiscal"],
                    "valor_total_centavos": total_cents,
                    "parcelas": int(data["quantidade_boletos"]),
                },
                conn=conn,
            )

    def delete_purchase(self, purchase_id: int) -> None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT numero_nota_fiscal, numero_boleto, valor_total_centavos FROM compras WHERE id = ?",
                (int(purchase_id),),
            ).fetchone()
            if not row:
                return
            self.audit_event(
                "lancamento_excluido",
                entity_type="lancamento",
                entity_id=purchase_id,
                details={
                    "nota": row["numero_nota_fiscal"],
                    "boleto": row["numero_boleto"],
                    "valor_total_centavos": row["valor_total_centavos"],
                },
                conn=conn,
            )
            conn.execute("DELETE FROM compras WHERE id = ?", (int(purchase_id),))

    def get_purchase(self, purchase_id: int) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT c.*, e.nome AS empresa, COALESCE(e.cnpj, '') AS cnpj
                  FROM compras c
                  JOIN empresas e ON e.id = c.empresa_id
                 WHERE c.id = ?
                """,
                (int(purchase_id),),
            ).fetchone()

    def _purchase_status_subquery(self) -> str:
        return """
            SELECT
                c.id,
                e.nome AS empresa,
                COALESCE(e.cnpj, '') AS cnpj,
                c.tipo_movimentacao,
                c.centro_custo,
                c.data_lancamento,
                c.numero_nota_fiscal,
                c.numero_boleto,
                c.quantidade_boletos,
                c.valor_nota_fiscal,
                c.valor_parte_especial,
                c.valor_total,
                c.valor_nota_fiscal_centavos,
                c.valor_parte_especial_centavos,
                c.valor_total_centavos,
                c.primeiro_vencimento,
                MIN(CASE WHEN b.pago = 0 THEN b.vencimento END) AS proximo_vencimento,
                SUM(CASE WHEN b.pago = 1 THEN 1 ELSE 0 END) AS boletos_pagos,
                COUNT(b.id) AS boletos_total,
                CASE
                    WHEN COUNT(b.id) = 0 THEN 'Pendente'
                    WHEN SUM(CASE WHEN b.pago = 0 AND b.vencimento < :today THEN 1 ELSE 0 END) > 0 THEN 'Atrasado'
                    WHEN SUM(CASE WHEN b.pago = 0 THEN 1 ELSE 0 END) = 0 THEN 'Em dia'
                    ELSE 'Pendente'
                END AS status,
                CASE
                    WHEN SUM(CASE WHEN b.pago = 0 AND b.vencimento = :tomorrow THEN 1 ELSE 0 END) > 0
                    THEN 1 ELSE 0
                END AS vence_amanha
            FROM compras c
            JOIN empresas e ON e.id = c.empresa_id
            LEFT JOIN boletos b ON b.compra_id = c.id
            GROUP BY c.id
        """

    def list_purchases(
        self,
        search: str = "",
        start_date: str | None = None,
        end_date: str | None = None,
        movement_type: str = "Todos",
        status: str = "Todos",
        cost_center: str = "Todos",
    ) -> list[sqlite3.Row]:
        search_terms = [t for t in search.strip().split() if t]
        params: dict[str, object] = {
            "today": today_db(),
            "tomorrow": (date.today() + timedelta(days=1)).strftime(DATE_FMT_DB),
            "start": start_date,
            "end": end_date,
            "type": movement_type,
            "status": status,
            "cost_center": cost_center,
        }
        where = [
            "(:start IS NULL OR data_lancamento >= :start)",
            "(:end IS NULL OR data_lancamento <= :end)",
            "(:type = 'Todos' OR tipo_movimentacao = :type)",
            "(:cost_center = 'Todos' OR centro_custo = :cost_center)",
        ]
        for idx, token in enumerate(search_terms):
            key = f"term{idx}"
            params[key] = f"%{token}%"
            where.append(
                f"(empresa LIKE :{key} OR cnpj LIKE :{key} OR numero_nota_fiscal LIKE :{key} "
                f"OR numero_boleto LIKE :{key} OR centro_custo LIKE :{key} OR tipo_movimentacao LIKE :{key})"
            )
        if status == "Vence amanhã":
            where.append("vence_amanha = 1")
        elif status == "Vence hoje":
            where.append("EXISTS (SELECT 1 FROM boletos bx WHERE bx.compra_id = q.id AND bx.pago = 0 AND bx.vencimento = :today)")
        elif status == "Próximos 3 dias":
            params["limit_date"] = (date.today() + timedelta(days=3)).strftime(DATE_FMT_DB)
            where.append("EXISTS (SELECT 1 FROM boletos bx WHERE bx.compra_id = q.id AND bx.pago = 0 AND bx.vencimento BETWEEN :today AND :limit_date)")
        elif status == "Próximos 7 dias":
            params["limit_date"] = (date.today() + timedelta(days=7)).strftime(DATE_FMT_DB)
            where.append("EXISTS (SELECT 1 FROM boletos bx WHERE bx.compra_id = q.id AND bx.pago = 0 AND bx.vencimento BETWEEN :today AND :limit_date)")
        else:
            where.append("(:status = 'Todos' OR status = :status)")

        sql = f"""
            SELECT * FROM ({self._purchase_status_subquery()}) q
             WHERE {' AND '.join(where)}
             ORDER BY data_lancamento DESC, id DESC
        """
        with self.connect() as conn:
            return conn.execute(sql, params).fetchall()

    def filtered_summary(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        movement_type: str = "Todos",
        cost_center: str = "Todos",
    ) -> dict:
        params = {
            "start": start_date,
            "end": end_date,
            "type": movement_type,
            "cost_center": cost_center,
            "today": today_db(),
            "tomorrow": (date.today() + timedelta(days=1)).strftime(DATE_FMT_DB),
        }
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS qtd,
                    COALESCE(SUM(CASE WHEN tipo_movimentacao = 'Entrada' THEN COALESCE(valor_total_centavos, CAST(ROUND(valor_total * 100) AS INTEGER)) ELSE 0 END), 0) AS entradas_centavos,
                    COALESCE(SUM(CASE WHEN tipo_movimentacao = 'Despesa' THEN COALESCE(valor_total_centavos, CAST(ROUND(valor_total * 100) AS INTEGER)) ELSE 0 END), 0) AS despesas_centavos
                FROM compras
                WHERE (:start IS NULL OR data_lancamento >= :start)
                  AND (:end IS NULL OR data_lancamento <= :end)
                  AND (:type = 'Todos' OR tipo_movimentacao = :type)
                  AND (:cost_center = 'Todos' OR centro_custo = :cost_center)
                """,
                params,
            ).fetchone()
            alert_row = conn.execute(
                """
                SELECT
                    SUM(CASE WHEN b.pago = 0 AND b.vencimento < :today THEN 1 ELSE 0 END) AS atrasados,
                    SUM(CASE WHEN b.pago = 0 AND b.vencimento = :tomorrow THEN 1 ELSE 0 END) AS amanha
                FROM boletos b
                JOIN compras c ON c.id = b.compra_id
                WHERE (:start IS NULL OR c.data_lancamento >= :start)
                  AND (:end IS NULL OR c.data_lancamento <= :end)
                  AND (:type = 'Todos' OR c.tipo_movimentacao = :type)
                  AND (:cost_center = 'Todos' OR c.centro_custo = :cost_center)
                """,
                params,
            ).fetchone()

        entradas = from_cents(int(row["entradas_centavos"] or 0))
        despesas = from_cents(int(row["despesas_centavos"] or 0))
        return {
            "qtd": int(row["qtd"] or 0),
            "entradas": entradas,
            "despesas": despesas,
            "saldo": entradas - despesas,
            "atrasados": int(alert_row["atrasados"] or 0),
            "amanha": int(alert_row["amanha"] or 0),
        }

    def monthly_summary(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        movement_type: str = "Todos",
        cost_center: str = "Todos",
    ) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT
                    substr(data_lancamento, 1, 7) AS mes,
                    COUNT(*) AS qtd,
                    COALESCE(SUM(CASE WHEN tipo_movimentacao = 'Entrada' THEN COALESCE(valor_total_centavos, CAST(ROUND(valor_total * 100) AS INTEGER)) ELSE 0 END), 0) AS entradas_centavos,
                    COALESCE(SUM(CASE WHEN tipo_movimentacao = 'Despesa' THEN COALESCE(valor_total_centavos, CAST(ROUND(valor_total * 100) AS INTEGER)) ELSE 0 END), 0) AS despesas_centavos
                FROM compras
                WHERE (:start IS NULL OR data_lancamento >= :start)
                  AND (:end IS NULL OR data_lancamento <= :end)
                  AND (:type = 'Todos' OR tipo_movimentacao = :type)
                  AND (:cost_center = 'Todos' OR centro_custo = :cost_center)
                GROUP BY substr(data_lancamento, 1, 7)
                ORDER BY mes DESC
                """,
                {"start": start_date, "end": end_date, "type": movement_type, "cost_center": cost_center},
            ).fetchall()

    def list_cost_centers(self) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT centro_custo FROM compras WHERE centro_custo IS NOT NULL AND trim(centro_custo) <> '' ORDER BY centro_custo COLLATE NOCASE"
            ).fetchall()
        values = list(COST_CENTERS)
        for row in rows:
            value = row["centro_custo"]
            if value not in values:
                values.append(value)
        return values
