from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .csv_utils import first_present, read_csv_rows, to_number


@dataclass(frozen=True)
class StatementAmount:
    account: str
    amount: float
    source: str


MONTH_COLUMNS = {
    1: ("1月", "01月", "2026/01", "2026-01", "jan"),
    2: ("2月", "02月", "2026/02", "2026-02", "feb"),
    3: ("3月", "03月", "2026/03", "2026-03", "mar"),
    4: ("4月", "04月", "apr"),
    5: ("5月", "05月", "may"),
    6: ("6月", "06月", "jun"),
    7: ("7月", "07月", "jul"),
    8: ("8月", "08月", "aug"),
    9: ("9月", "09月", "sep"),
    10: ("10月", "oct"),
    11: ("11月", "nov"),
    12: ("12月", "dec"),
}


def load_pl_amounts(path: str | Path, months: list[int]) -> list[StatementAmount]:
    return _load_statement_amounts(path, months)


def _load_statement_amounts(path: str | Path, months: list[int]) -> list[StatementAmount]:
    rows = read_csv_rows(path)
    amounts: list[StatementAmount] = []
    for row in rows:
        account = first_present(row, ("勘定科目", "科目", "account", "account_name", "name"))
        if not account:
            continue
        total = 0.0
        used_columns: list[str] = []
        for month in months:
            for column in MONTH_COLUMNS[month]:
                if column.lower() in row:
                    total += to_number(row[column.lower()])
                    used_columns.append(column)
                    break
        if not used_columns:
            total = to_number(first_present(row, ("合計", "total", "金額", "amount")))
        amounts.append(StatementAmount(account=account, amount=total, source=f"{Path(path).name}:{account}"))
    return amounts

