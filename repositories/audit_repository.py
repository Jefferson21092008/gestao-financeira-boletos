import json
import sqlite3
from typing import Any

from core.dates import now_iso


class AuditRepositoryMixin:
    current_user: str | None = None

    def audit_event(
        self,
        action: str,
        *,
        entity_type: str = "sistema",
        entity_id: int | str | None = None,
        details: dict[str, Any] | None = None,
        actor: str | None = None,
        conn: sqlite3.Connection | None = None,
    ) -> int:
        payload = json.dumps(details or {}, ensure_ascii=False, default=str)
        owner = actor or getattr(self, "current_user", None) or "sistema"
        own_conn = conn is None
        if own_conn:
            conn = self.connect()
        assert conn is not None
        try:
            cur = conn.execute(
                """
                INSERT INTO auditoria (ator, acao, entidade_tipo, entidade_id, detalhes_json, criado_em)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (owner, action, entity_type, None if entity_id is None else str(entity_id), payload, now_iso()),
            )
            if own_conn:
                conn.commit()
            return int(cur.lastrowid)
        finally:
            if own_conn:
                conn.close()

    def list_audit_events(self, limit: int = 500) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT id, ator, acao, entidade_tipo, entidade_id, detalhes_json, criado_em
                  FROM auditoria
                 ORDER BY id DESC
                 LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()
