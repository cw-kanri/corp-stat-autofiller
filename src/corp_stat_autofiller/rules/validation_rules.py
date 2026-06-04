from __future__ import annotations

from typing import Any

from corp_stat_autofiller.models import FillPlanItem, ValidationIssue


def validate_fill_plan(plan: list[FillPlanItem], rules: dict[str, Any]) -> list[ValidationIssue]:
    values = {item.item_id: item.value for item in plan}
    return [
        *validate_input_values(values, rules),
        *validate_formula_values(values, rules),
    ]


def validate_input_values(values: dict[str, Any], rules: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    for item_id in rules.get("required_items", []):
        item_id = str(item_id)
        if item_id not in values or values[item_id] in (None, ""):
            issues.append(ValidationIssue("error", "required_missing", f"Required item [{item_id}] is missing.", [item_id]))

    for item_id in rules.get("non_negative_items", []):
        item_id = str(item_id)
        value = values.get(item_id)
        if isinstance(value, int | float) and value < 0:
            issues.append(ValidationIssue("error", "negative_not_allowed", f"Item [{item_id}] must not be negative.", [item_id]))

    if "payroll" in rules and "56" not in values and "57" not in values:
        issues.append(ValidationIssue("warning", "payroll_missing", "Payroll items are missing.", ["56", "57"]))
    return issues


def validate_formula_values(values: dict[str, Any], rules: dict[str, Any]) -> list[ValidationIssue]:
    formula_values = _with_computed_items(values, rules)
    default_zero_ids = set(str(item_id) for item_id in rules.get("formula_default_zero_items", []))
    issues: list[ValidationIssue] = []

    for check in rules.get("balance_checks", []):
        check_default_zero_ids = set(default_zero_ids)
        if check.get("default_missing_to_zero", False):
            check_default_zero_ids.update(_ids_in_expr(check))
        left = _eval_expr(str(check["left"]), formula_values, check_default_zero_ids)
        right = _eval_expr(str(check["right"]), formula_values, check_default_zero_ids)
        tolerance = float(check.get("tolerance", 0))
        if left is None or right is None:
            issues.append(
                ValidationIssue(
                    "warning",
                    "formula_check_skipped",
                    f"{check['label']} formula check was skipped because source values are missing.",
                    _ids_in_expr(check),
                )
            )
            continue
        if abs(left - right) > tolerance:
            issues.append(
                ValidationIssue(
                    "error",
                    "formula_mismatch",
                    f"{check['label']} does not match: {left} != {right}",
                    _ids_in_expr(check),
                )
            )
    return issues


def _with_computed_items(values: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    result = dict(values)
    computed_items = {str(item_id): str(expr) for item_id, expr in rules.get("computed_items", {}).items()}
    default_zero_ids = set(str(item_id) for item_id in rules.get("formula_default_zero_items", []))
    for _ in range(max(1, len(computed_items))):
        changed = False
        for item_id, expr in computed_items.items():
            if item_id in result:
                continue
            value = _eval_expr(expr, result, default_zero_ids)
            if value is not None:
                result[item_id] = value
                changed = True
        if not changed:
            break
    return result


def _eval_expr(expr: str, values: dict[str, Any], default_zero_ids: set[str] | None = None) -> float | None:
    default_zero_ids = default_zero_ids or set()
    env: dict[str, float] = {}
    rewritten = expr
    for item_id in _ids_from_text(expr):
        name = f"i_{item_id}"
        value = values.get(item_id, 0 if item_id in default_zero_ids else None)
        if not isinstance(value, int | float):
            return None
        rewritten = rewritten.replace(f"[{item_id}]", name)
        env[name] = float(value)
    try:
        return float(eval(rewritten, {"__builtins__": {}}, env))
    except NameError:
        return None


def _ids_in_expr(check: dict[str, Any]) -> list[str]:
    return _ids_from_text(f"{check.get('left', '')} {check.get('right', '')}")


def _ids_from_text(text: str) -> list[str]:
    ids: list[str] = []
    for part in text.split("[")[1:]:
        ids.append(part.split("]", maxsplit=1)[0])
    return ids
