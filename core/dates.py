import calendar
from datetime import date, datetime

from config import DATE_FMT_DB


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_db() -> str:
    return date.today().strftime(DATE_FMT_DB)


def add_months(base_date: date, months: int) -> date:
    month_index = base_date.month - 1 + months
    year = base_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(base_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def status_from_values(paid: int, due_date: str) -> str:
    if paid:
        return "Em dia"
    if due_date < today_db():
        return "Atrasado"
    return "Pendente"
