from config import DEFAULT_USER
from core.dates import now_iso
from core.security import hash_password, validate_new_password, verify_password


class AuthRepositoryMixin:
    def has_users(self) -> bool:
        with self.connect() as conn:
            return conn.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone() is not None

    def create_initial_admin(self, password: str, username: str = DEFAULT_USER) -> None:
        username = username.strip() or DEFAULT_USER
        validate_new_password(password)
        with self.connect() as conn:
            if conn.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone():
                raise ValueError("O acesso inicial já foi configurado.")
            password_hash, salt = hash_password(password)
            cur = conn.execute(
                """
                INSERT INTO usuarios (
                    usuario, senha_hash, salt, criado_em, must_change_password, ultimo_login_em
                ) VALUES (?, ?, ?, ?, 0, NULL)
                """,
                (username, password_hash, salt, now_iso()),
            )
            self.audit_event(
                "usuario_inicial_criado",
                entity_type="usuario",
                entity_id=int(cur.lastrowid),
                details={"usuario": username},
                actor=username,
                conn=conn,
            )
        self.current_user = username

    def authenticate(self, username: str, password: str) -> bool:
        username = username.strip()
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id, senha_hash, salt FROM usuarios WHERE usuario = ?",
                (username,),
            ).fetchone()
            ok = bool(row and verify_password(password, row["senha_hash"], row["salt"]))
            if ok:
                conn.execute(
                    "UPDATE usuarios SET ultimo_login_em = ? WHERE id = ?",
                    (now_iso(), int(row["id"])),
                )
                self.audit_event(
                    "login_sucesso",
                    entity_type="usuario",
                    entity_id=int(row["id"]),
                    details={"usuario": username},
                    actor=username,
                    conn=conn,
                )
            else:
                self.audit_event(
                    "login_falhou",
                    entity_type="usuario",
                    details={"usuario": username},
                    actor=username or "desconhecido",
                    conn=conn,
                )
        if ok:
            self.current_user = username
        return ok

    def user_requires_password_change(self, username: str) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT must_change_password FROM usuarios WHERE usuario = ?",
                (username.strip(),),
            ).fetchone()
        return bool(row and int(row["must_change_password"] or 0))

    def force_change_password(self, username: str, new_password: str) -> None:
        validate_new_password(new_password)
        username = username.strip()
        password_hash, salt = hash_password(new_password)
        with self.connect() as conn:
            row = conn.execute("SELECT id FROM usuarios WHERE usuario = ?", (username,)).fetchone()
            if not row:
                raise ValueError("Usuário não encontrado.")
            conn.execute(
                """
                UPDATE usuarios
                   SET senha_hash = ?, salt = ?, must_change_password = 0
                 WHERE id = ?
                """,
                (password_hash, salt, int(row["id"])),
            )
            self.audit_event(
                "senha_alterada",
                entity_type="usuario",
                entity_id=int(row["id"]),
                details={"usuario": username},
                actor=username,
                conn=conn,
            )

    def end_session(self) -> None:
        if getattr(self, "current_user", None):
            self.audit_event("logout", entity_type="usuario", actor=self.current_user)
        self.current_user = None

