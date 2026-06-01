from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook
from openpyxl.workbook import Workbook


def load_survey_workbook(path: str | Path, keep_formulas: bool = True) -> Workbook:
    return load_workbook(Path(path), data_only=not keep_formulas)

