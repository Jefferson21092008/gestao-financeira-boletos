import sqlite3
from datetime import date, timedelta

from config import DATE_FMT_DB


class BillRepositoryMixin:
    def list_bills(self, purchase_id: int) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT b.*, e.nome AS empresa, c.numero_nota_fiscal
                  FROM boletos b
                  JOIN compras c ON c.id = b.compra_id
                  JOIN empresas e ON e.id = c.empresa_id
                 WHERE b.compra_id = ?
                 ORDER BY b.parcela
                """,
                (int(purchase_id),),
            ).fetchall()

    def set_bill_paid(self, bill_id: int, paid: bool, payment_date: str | None = None) -> None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id, compra_id, parcela, pago, data_pagamento FROM boletos WHERE id = ?",
                (int(bill_id),),
            ).fetchone()
            if not row:
                raise ValueError("Boleto não encontrado.")
            new_paid = 1 if paid else 0
            new_date = payment_date if paid else None
            conn.execute(
                "UPDATE boletos SET pago = ?, data_pagamento = ? WHERE id = ?",
                (new_paid, new_date, int(bill_id)),
            )
            self.audit_event(
                "boleto_pago" if paid else "boleto_reaberto",
                entity_type="boleto",
                entity_id=bill_id,
                details={
                    "compra_id": int(row["compra_id"]),
                    "parcela": int(row["parcela"]),
                    "data_pagamento": new_date,
                    "estado_anterior_pago": int(row["pago"]),
                },
                conn=conn,
            )

    def update_bill_due_date(self, bill_id: int, due_date: str) -> None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT vencimento, compra_id, parcela FROM boletos WHERE id = ?",
                (int(bill_id),),
            ).fetchone()
            if not row:
                raise ValueError("Boleto não encontrado.")
            conn.execute("UPDATE boletos SET vencimento = ? WHERE id = ?", (due_date, int(bill_id)))
            self.audit_event(
                "vencimento_boleto_alterado",
                entity_type="boleto",
                entity_id=bill_id,
                details={
                    "compra_id": int(row["compra_id"]),
                    "parcela": int(row["parcela"]),
                    "vencimento_anterior": row["vencimento"],
                    "novo_vencimento": due_date,
                },
                conn=conn,
            )

    def list_alerts(self, alert_filter: str = "Todos") -> list[sqlite3.Row]:
        today = date.today()
        limits = {
            "today": today.strftime(DATE_FMT_DB),
            "tomorrow": (today + timedelta(days=1)).strftime(DATE_FMT_DB),
            "d3": (today + timedelta(days=3)).strftime(DATE_FMT_DB),
            "d7": (today + timedelta(days=7)).strftime(DATE_FMT_DB),
            "filter": alert_filter,
        }
        where_filter = {
            "Todos": "b.vencimento <= :d7",
            "Atrasado": "b.vencimento < :today",
            "Vence hoje": "b.vencimento = :today",
            "Vence amanhã": "b.vencimento = :tomorrow",
            "Próximos 3 dias": "b.vencimento BETWEEN :today AND :d3",
            "Próximos 7 dias": "b.vencimento BETWEEN :today AND :d7",
        }.get(alert_filter, "b.vencimento <= :d7")
        with self.connect() as conn:
            return conn.execute(
                f"""
                SELECT
                    b.id AS boleto_id,
                    b.compra_id,
                    e.nome AS empresa,
                    c.numero_nota_fiscal,
                    b.numero_boleto,
                    b.parcela,
                    b.vencimento,
                    b.valor,
                    b.valor_centavos,
                    CAST(julianday(b.vencimento) - julianday(:today) AS INTEGER) AS dias,
                    CASE
                        WHEN b.vencimento < :today THEN 'Atrasado'
                        WHEN b.vencimento = :today THEN 'Vence hoje'
                        WHEN b.vencimento = :tomorrow THEN 'Vence amanhã'
                        WHEN b.vencimento <= :d3 THEN 'Até 3 dias'
                        ELSE 'Até 7 dias'
                    END AS alerta
                FROM boletos b
                JOIN compras c ON c.id = b.compra_id
                JOIN empresas e ON e.id = c.empresa_id
                WHERE b.pago = 0 AND ({where_filter})
                ORDER BY b.vencimento ASC, e.nome COLLATE NOCASE
                """,
                limits,
            ).fetchall()

    def alert_counts_detailed(self) -> dict[str, int]:
        today = date.today()
        params = {
            "today": today.strftime(DATE_FMT_DB),
            "tomorrow": (today + timedelta(days=1)).strftime(DATE_FMT_DB),
            "d3": (today + timedelta(days=3)).strftime(DATE_FMT_DB),
            "d7": (today + timedelta(days=7)).strftime(DATE_FMT_DB),
        }
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    SUM(CASE WHEN pago = 0 AND vencimento < :today THEN 1 ELSE 0 END) AS atrasados,
                    SUM(CASE WHEN pago = 0 AND vencimento = :today THEN 1 ELSE 0 END) AS hoje,
                    SUM(CASE WHEN pago = 0 AND vencimento = :tomorrow THEN 1 ELSE 0 END) AS amanha,
                    SUM(CASE WHEN pago = 0 AND vencimento BETWEEN :today AND :d3 THEN 1 ELSE 0 END) AS d3,
                    SUM(CASE WHEN pago = 0 AND vencimento BETWEEN :today AND :d7 THEN 1 ELSE 0 END) AS d7
                FROM boletos
                """,
                params,
            ).fetchone()
        return {key: int(row[key] or 0) for key in ("atrasados", "hoje", "amanha", "d3", "d7")}

    def alert_counts(self) -> tuple[int, int]:
        counts = self.alert_counts_detailed()
        return counts["atrasados"], counts["amanha"]
