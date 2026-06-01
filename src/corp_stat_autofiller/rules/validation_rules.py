from __future__ import annotations

from typing import Any

from corp_stat_autofiller.models import FillPlanItem, ValidationIssue


def validate_fill_plan(plan: list[FillPlanItem], rules: dict[str, Any]) -> list[ValidationIssue]:
    values = {item.item_id: item.value for item in plan}
    issues: list[ValidationIssue] = []

    for item_id in rules.get("required_items", []):
        if item_id not in values or values[item_id] in (None, ""):
            issues.append(ValidationIssue("error", "required_missing", f"必須項目[{item_id}]が未入力です。", [item_id]))

    for item_id in rules.get("non_negative_items", []):
        value = values.get(str(item_id))
        if isinstance(value, int | float) and value < 0:
            issues.append(ValidationIssue("error", "negative_not_allowed", f"マイナス不可項目[{item_id}]に負値があります。", [str(item_id)]))

    for check in rules.get("balance_checks", []):
        left = _eval_expr(str(check["left"]), values)
        right = _eval_expr(str(check["right"]), values)
        tolerance = float(check.get("tolerance", 0))
        if left is None or right is None:
            issues.append(ValidationIssue("warning", "check_skipped", f"{check['label']} は入力不足のため検証できません。", _ids_in_expr(check)))
            continue
        if abs(left - right) > tolerance:
            issues.append(
                ValidationIssue(
                    "error",
                    "balance_mismatch",
                    f"{check['label']} が一致しません: {left} != {right}",
                    _ids_in_expr(check),
                )
            )

    if "56" not in values and "57" not in values:
        issues.append(ValidationIssue("warning", "payroll_missing", "人件費項目が入力されていません。", ["56", "57"]))
    return issues


def _eval_expr(expr: str, values: dict[str, Any]) -> float | None:
    env: dict[str, float] = {}
    rewritten = expr
    for item_id, value in values.items():
        name = f"i_{item_id}"
        rewritten = rewritten.replace(f"[{item_id}]", name)
        if isinstance(value, int | float):
            env[name] = float(value)
    if "[" in rewritten:
        return None
    try:
        return float(eval(rewritten, {"__builtins__": {}}, env))
    except NameError:
        return None


def _ids_in_expr(check: dict[str, Any]) -> list[str]:
    text = f"{check.get('left', '')} {check.get('right', '')}"
    ids: list[str] = []
    for part in text.split("[")[1:]:
        ids.append(part.split("]", maxsplit=1)[0])
    return ids

