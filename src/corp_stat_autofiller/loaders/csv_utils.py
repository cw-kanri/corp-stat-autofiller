from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable


ENCODINGS = ("utf-8-sig", "utf-8", "cp932")


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    csv_path = Path(path)
    last_error: UnicodeDecodeError | None = None
    for encoding in ENCODINGS:
        try:
            with csv_path.open("r", encoding=encoding, newline="") as handle:
                reader = csv.DictReader(handle)
                return [{normalize_header(k): (v or "").strip() for k, v in row.items()} for row in reader]
        except UnicodeDecodeError as exc:
            last_error = exc
    raise ValueError(f"CSVを読み込めませんでした: {csv_path}。UTF-8/CP932を確認してください。") from last_error


def normalize_header(value: str | None) -> str:
    return (value or "").strip().replace("　", " ").lower()


def first_present(row: dict[str, str], names: Iterable[str]) -> str:
    for name in names:
        value = row.get(normalize_header(name))
        if value not in (None, ""):
            return value
    return ""


def to_number(value: str | int | float | None) -> float:
    if value is None:
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    cleaned = (
        value.strip()
        .replace(",", "")
        .replace("￥", "")
        .replace("¥", "")
        .replace("△", "-")
    )
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = f"-{cleaned[1:-1]}"
    if cleaned in ("", "-"):
        return 0.0
    return float(cleaned)

