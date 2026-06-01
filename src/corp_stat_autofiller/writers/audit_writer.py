from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from corp_stat_autofiller.models import AuditEvent, FillPlanItem, InputValue, UnresolvedItem, ValidationIssue


def write_outputs(
    output_dir: str | Path,
    input_values: list[InputValue],
    fill_plan: list[FillPlanItem],
    unresolved: list[UnresolvedItem],
    issues: list[ValidationIssue],
    events: list[AuditEvent],
) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "input_values.json", [item.to_dict() for item in input_values])
    _write_json(output / "fill_plan.json", [item.to_dict() for item in fill_plan])
    _write_json(output / "audit_log.json", [event.to_dict() for event in events])
    _write_unresolved(output / "unresolved_items.csv", unresolved)
    _write_validation_report(output / "validation_report.md", issues)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_unresolved(path: Path, unresolved: list[UnresolvedItem]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item_id", "label", "reason", "candidates"])
        writer.writeheader()
        for item in unresolved:
            writer.writerow(item.to_row())


def _write_validation_report(path: Path, issues: list[ValidationIssue]) -> None:
    lines = ["# validation_report", ""]
    if not issues:
        lines.append("重大な検証エラーはありません。")
    else:
        for issue in issues:
            lines.append(f"- **{issue.severity}** `{issue.code}`: {issue.message}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

