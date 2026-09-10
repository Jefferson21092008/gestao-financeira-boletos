from pathlib import Path

from database.connection import DatabaseConnection
from database.schema import SchemaMixin
from repositories.audit_repository import AuditRepositoryMixin
from repositories.auth_repository import AuthRepositoryMixin
from repositories.backup_repository import BackupRepositoryMixin
from repositories.bill_repository import BillRepositoryMixin
from repositories.company_repository import CompanyRepositoryMixin
from repositories.fraud_repository import FraudRepositoryMixin
from repositories.purchase_repository import PurchaseRepositoryMixin


class Database(
    SchemaMixin,
    AuditRepositoryMixin,
    AuthRepositoryMixin,
    CompanyRepositoryMixin,
    PurchaseRepositoryMixin,
    BillRepositoryMixin,
    FraudRepositoryMixin,
    BackupRepositoryMixin,
    DatabaseConnection,
):
    """Fachada de compatibilidade para o restante da aplicação.

    O acesso a dados foi dividido por domínio, mas as telas continuam recebendo
    uma única instância de Database. Isso reduz o acoplamento sem alterar o fluxo
    funcional das versões anteriores.
    """

    def __init__(self, path: Path):
        DatabaseConnection.__init__(self, path)
        self.create_schema()
        self.migrate_schema()
        self.current_user = None
