from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .csv_utils import first_present, normalize_header, read_csv_rows, to_number


@dataclass(frozen=True)
class PayrollRecord:
    employee_id: str
    employee_name: str
    role: str
    values: dict[str, float]
    source: str


NAME_COLUMNS = (
    "\u5f93\u696d\u54e1",
    "\u6c0f\u540d",
    "employee_name",
    "name",
)
ID_COLUMNS = (
    "\u5f93\u696d\u54e1\u756a\u53f7",
    "\u793e\u54e1\u756a\u53f7",
    "employee_id",
    "id",
)
ROLE_COLUMNS = (
    "\u5f79\u8077",
    "\u96c7\u7528\u533a\u5206",
    "\u533a\u5206",
    "role",
)
TOTAL_MARKERS = {"-", "\u5408\u8a08", "\u7dcf\u8a08", "total"}


def load_payroll_records(paths: list[str | Path]) -> list[PayrollRecord]:
    records: list[PayrollRecord] = []
    for path in paths:
        for row in read_csv_rows(path):
            ordered_keys = list(row.keys())
            name = first_present(row, NAME_COLUMNS)
            employee_id = first_present(row, ID_COLUMNS)
            role = first_present(row, ROLE_COLUMNS)
            metadata_keys = _matched_metadata_keys(row)

            used_positional_fallback = False
            if not name and not employee_id and len(ordered_keys) >= 2:
                employee_id = row.get(ordered_keys[0], "")
                name = row.get(ordered_keys[1], "")
                metadata_keys.update(ordered_keys[:2])
                used_positional_fallback = True
            if not role and used_positional_fallback and len(ordered_keys) >= 3:
                role = row.get(ordered_keys[2], "")
                metadata_keys.add(ordered_keys[2])

            if not name and not employee_id:
                continue
            if _is_total_row(name, employee_id):
                continue

            values: dict[str, float] = {}
            for key, value in row.items():
                if key in metadata_keys:
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


def _matched_metadata_keys(row: dict[str, str]) -> set[str]:
    candidates = {normalize_header(column) for column in NAME_COLUMNS + ID_COLUMNS + ROLE_COLUMNS}
    return {key for key in row if key in candidates}


def _is_total_row(name: str, employee_id: str) -> bool:
    normalized = {name.strip().lower(), employee_id.strip().lower()}
    return bool(normalized & TOTAL_MARKERS)
