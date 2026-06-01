from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"設定ファイルの形式が不正です: {path}")
    return data


def quarter_to_months(quarter: str) -> list[int]:
    try:
        q = int(quarter.upper().split("Q", maxsplit=1)[1])
    except (IndexError, ValueError) as exc:
        raise ValueError("quarter は 2026Q1 のような形式で指定してください。") from exc
    ranges = {1: [1, 2, 3], 2: [4, 5, 6], 3: [7, 8, 9], 4: [10, 11, 12]}
    if q not in ranges:
        raise ValueError("quarter の四半期は Q1 から Q4 で指定してください。")
    return ranges[q]

