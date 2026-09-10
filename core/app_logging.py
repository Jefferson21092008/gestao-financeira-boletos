import logging
from logging.handlers import RotatingFileHandler

from core.paths import get_app_data_dir


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("gestao_empresas")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    path = get_app_data_dir() / "gestao_empresas.log"
    handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
    return logger
