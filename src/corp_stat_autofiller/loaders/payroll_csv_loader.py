from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .csv_utils import first_present, read_csv_rows, to_number


@dataclass(frozen=True)
class PayrollRecord:
    employee_id: str
    employee_name: str
    role: str
    values: dict[str, float]
    source: str


def load_payroll_records(paths: list[str | Path]) -> list[PayrollRecord]:
    records: list[PayrollRecord] = []
    for path in paths:
        for row in read_csv_rows(path):
            name = first_present(row, ("氏名", "従業員名", "employee_name", "name"))
            employee_id = first_present(row, ("社員番号", "従業員番号", "employee_id", "id"))
            if not name and not employee_id:
                continue
            role = first_present(row, ("役職区分", "雇用区分", "区分", "role"))
            values: dict[str, float] = {}
            for key, value in row.items():
                if key in {"氏名", "従業員名", "employee_name", "name", "社員番号", "従業員番号", "employee_id", "id", "役職区分", "雇用区分", "区分", "role"}:
                    continue
                try:
                    values[key] = to_number(value)
                except ValueError:
                    continue
            records.append(
                PayrollRecord(
                    employee_id=employee_id,
                    employee_name=name,
                    role=role,
                    values=values,
                    source=f"{Path(path).name}:{employee_id or name}",
                )
            )
    return records
