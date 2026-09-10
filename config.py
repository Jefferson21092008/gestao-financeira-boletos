APP_NAME = "Gestão Financeira de Empresas"
APP_FOLDER = "GestaoEmpresasLocal"
DB_NAME = "gestao_empresas.db"
APP_VERSION = "12.1.3"

DEFAULT_USER = "admin"
PBKDF2_ITERATIONS = 240_000
MIN_PASSWORD_LENGTH = 8

DATE_FMT_UI = "%d/%m/%Y"
DATE_FMT_DB = "%Y-%m-%d"

MOVEMENT_TYPES = ("Entrada", "Despesa")
STATUS_OPTIONS = (
    "Todos", "Pendente", "Em dia", "Atrasado",
    "Vence hoje", "Vence amanhã", "Próximos 3 dias", "Próximos 7 dias",
)
COST_CENTERS = (
    "Administrativo", "Financeiro", "Operacional",
    "Comercial", "TI", "Estoque", "Outros",
)
ALERT_FILTERS = (
    "Todos", "Atrasado", "Vence hoje", "Vence amanhã",
    "Próximos 3 dias", "Próximos 7 dias",
)

BRASILAPI_CNPJ_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
RECEITA_CNPJ_PORTAL_URL = "https://www.gov.br/pt-br/servicos/consultar-cadastro-nacional-de-pessoas-juridicas"
CNPJ_CACHE_HOURS = 24
HTTP_TIMEOUT_SECONDS = 8
