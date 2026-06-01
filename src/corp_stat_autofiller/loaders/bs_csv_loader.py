from __future__ import annotations

from pathlib import Path

from .pl_csv_loader import StatementAmount, _load_statement_amounts


def load_bs_amounts(path: str | Path, months: list[int]) -> list[StatementAmount]:
    return _load_statement_amounts(path, months)

