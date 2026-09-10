import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
from core.paths import BACKUP_DIR


class BackupRepositoryMixin:
    def create_backup(self, label: str = "manual", keep_last: int = 30) -> Path:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_label = "".join(ch for ch in label.lower() if ch.isalnum() or ch in ("-", "_")) or "backup"
        destination = BACKUP_DIR / f"gestao_empresas_{stamp}_{safe_label}.db"
        source_conn = self.connect()
        try:
            target_conn = sqlite3.connect(destination)
            try:
                source_conn.backup(target_conn)
            finally:
                target_conn.close()
        finally:
            source_conn.close()
        backups = sorted(BACKUP_DIR.glob("gestao_empresas_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in backups[keep_last:]:
            try:
                old.unlink()
            except OSError:
                pass
        self.audit_event(
            "backup_criado",
            entity_type="backup",
            details={"arquivo": destination.name, "rotulo": safe_label},
        )
        return destination

    def create_daily_backup_if_needed(self) -> Path | None:
        today_prefix = datetime.now().strftime("%Y%m%d")
        if any(BACKUP_DIR.glob(f"gestao_empresas_{today_prefix}_*_automatico.db")):
            return None
        return self.create_backup("automatico")

    def list_backups(self) -> list[Path]:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        return sorted(BACKUP_DIR.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)

    def validate_backup_file(self, backup_path: Path) -> None:
        backup_path = Path(backup_path)
        if not backup_path.exists() or not backup_path.is_file():
            raise FileNotFoundError("Arquivo de backup não encontrado.")
        try:
            uri = backup_path.resolve().as_uri() + "?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
            try:
                check = conn.execute("PRAGMA quick_check").fetchone()
                if not check or str(check[0]).lower() != "ok":
                    raise ValueError("O arquivo SQLite falhou na verificação de integridade.")
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                required = {"usuarios", "empresas", "compras", "boletos"}
                missing = required - tables
                if missing:
                    raise ValueError("O arquivo não é um backup válido deste sistema. Tabelas ausentes: " + ", ".join(sorted(missing)))
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise ValueError(f"Arquivo de backup SQLite inválido: {exc}") from exc


    def export_backup(self, destination: Path, source_backup: Path | None = None) -> Path:
        """Cria/copia um backup validado para um destino externo escolhido pelo usuário."""
        destination = Path(destination)
        if destination.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
            destination = destination.with_suffix(".db")
        destination.parent.mkdir(parents=True, exist_ok=True)

        source = Path(source_backup) if source_backup else self.create_backup("exportacao")
        self.validate_backup_file(source)
        try:
            if source.resolve() == destination.resolve():
                raise ValueError("Escolha um local diferente do arquivo de backup de origem.")
        except OSError:
            pass

        shutil.copy2(source, destination)
        self.validate_backup_file(destination)
        self.audit_event(
            "backup_exportado",
            entity_type="backup",
            details={"origem": source.name, "destino": str(destination)},
        )
        return destination

    def restore_backup(self, backup_path: Path) -> None:
        backup_path = Path(backup_path)
        self.validate_backup_file(backup_path)
        try:
            if backup_path.resolve() == self.path.resolve():
                raise ValueError("O arquivo selecionado já é o banco de dados em uso.")
        except OSError:
            pass

        # Salva uma cópia de segurança do estado atual antes da restauração.
        self.create_backup("antes_restauracao")
        source = sqlite3.connect(backup_path)
        try:
            target = sqlite3.connect(self.path)
            try:
                source.backup(target)
            finally:
                target.close()
        finally:
            source.close()
        self.create_schema()
        self.migrate_schema()
        self.audit_event(
            "backup_restaurado",
            entity_type="backup",
            details={"arquivo": backup_path.name},
        )
