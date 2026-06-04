from __future__ import annotations

from collections import defaultdict
from typing import Any

from corp_stat_autofiller.loaders.payroll_csv_loader import PayrollRecord
from corp_stat_autofiller.models import InputValue, UnresolvedItem
from corp_stat_autofiller.rules.business_rules import to_million_yen


OFFICER_WORDS = ("\u5f79\u54e1", "\u53d6\u7de0\u5f79", "\u4ee3\u8868")
TEMP_WORDS = ("\u6d3e\u9063",)
DEFAULT_FIELDS = {
    "officer_salary": ("\u5f79\u54e1\u5831\u916c(\u652f\u7d66)",),
    "employee_salary": (
        "\u57fa\u672c\u7d66(\u652f\u7d66)",
        "\u8077\u80fd\u7d66(\u652f\u7d66)",
    ),
    "welfare_expense": (),
    "officer_bonus": ("\u5f79\u54e1\u8cde\u4e0e(\u652f\u7d66)",),
    "employee_bonus": ("\u8cde\u4e0e(\u652f\u7d66)",),
}


def resolve_payroll_values(
    records: list[PayrollRecord],
    rules: dict[str, Any],
    payroll_basis: str | None,
) -> tuple[list[InputValue], list[UnresolvedItem]]:
    if payroll_basis not in {"paid_month", "worked_month"}:
        return [], [
            UnresolvedItem(
                item_id="payroll_basis",
                label="payroll basis",
                reason="--payroll-basis must be paid_month or worked_month.",
                candidates=["paid_month", "worked_month"],
            )
        ]

    payroll_rules = rules.get("payroll", {})
    fields = payroll_rules.get("fields", {})
    field_sets = {
        key: _normalized_fields(fields.get(key, []), DEFAULT_FIELDS[key])
        for key in DEFAULT_FIELDS
    }

    officer_keys: set[str] = set()
    employee_keys: set[str] = set()
    officer_keys_by_period: dict[str, set[str]] = defaultdict(set)
    employee_keys_by_period: dict[str, set[str]] = defaultdict(set)
    totals: dict[str, float] = defaultdict(float)
    trace: dict[str, list[str]] = defaultdict(list)

    for record in records:
        role_text = f"{record.role} {record.employee_name}"
        is_temp = any(word in role_text for word in TEMP_WORDS)
        has_officer_pay = _record_total(record, field_sets["officer_salary"] | field_sets["officer_bonus"]) != 0
        is_officer = any(word in role_text for word in OFFICER_WORDS) or has_officer_pay
        has_employee_pay = _record_total(record, field_sets["employee_salary"] | field_sets["employee_bonus"]) != 0
        person_key = record.employee_id or record.employee_name
        period_key = record.source.split(":", maxsplit=1)[0]
        if is_temp:
            continue
        if is_officer:
            officer_keys.add(person_key)
            if has_officer_pay:
                officer_keys_by_period[period_key].add(person_key)
        elif has_employee_pay:
            employee_keys.add(person_key)
            employee_keys_by_period[period_key].add(person_key)

        for key, amount in record.values.items():
            normalized = _normalize(key)
            if normalized in field_sets["welfare_expense"]:
                totals["welfare_expense"] += amount
                trace["welfare_expense"].append(f"{record.source}:{key}")
            if is_officer and normalized in field_sets["officer_salary"]:
                totals["officer_salary"] += amount
                trace["officer_salary"].append(f"{record.source}:{key}")
            if not is_officer and normalized in field_sets["employee_salary"]:
                totals["employee_salary"] += amount
                trace["employee_salary"].append(f"{record.source}:{key}")
            if is_officer and normalized in field_sets["officer_bonus"]:
                totals["officer_bonus"] += amount
                trace["officer_bonus"].append(f"{record.source}:{key}")
            if not is_officer and normalized in field_sets["employee_bonus"]:
                totals["employee_bonus"] += amount
                trace["employee_bonus"].append(f"{record.source}:{key}")

    months_in_quarter = max(1, payroll_rules.get("months_in_quarter", 3))
    employee_average = _average_monthly_count(employee_keys_by_period, len(employee_keys), months_in_quarter)
    values = [
        InputValue("54", "officer_count", len(officer_keys), "people", "payroll", sorted(officer_keys)),
        InputValue("55", "employee_count", employee_average, "people", "payroll", sorted(employee_keys)),
        InputValue("56", "officer_salary", to_million_yen(totals["officer_salary"]), "million_yen", "payroll", trace["officer_salary"]),
        InputValue("57", "employee_salary", to_million_yen(totals["employee_salary"]), "million_yen", "payroll", trace["employee_salary"]),
        InputValue("58", "welfare_expense", to_million_yen(totals["welfare_expense"]), "million_yen", "payroll", trace["welfare_expense"]),
        InputValue("60", "officer_bonus", to_million_yen(totals["officer_bonus"]), "million_yen", "payroll", trace["officer_bonus"]),
        InputValue("61", "employee_bonus", to_million_yen(totals["employee_bonus"]), "million_yen", "payroll", trace["employee_bonus"]),
    ]
    return values, []


def _normalized_fields(configured: list[str], defaults: tuple[str, ...]) -> set[str]:
    return {_normalize(field) for field in [*configured, *defaults]}


def _record_total(record: PayrollRecord, fields: set[str]) -> float:
    return sum(amount for key, amount in record.values.items() if _normalize(key) in fields)


def _average_monthly_count(keys_by_period: dict[str, set[str]], fallback_count: int, months_in_quarter: int) -> float:
    if keys_by_period:
        return round(sum(len(keys) for keys in keys_by_period.values()) / months_in_quarter)
    return round(fallback_count / months_in_quarter)


def _normalize(value: str) -> str:
    return value.strip().replace("\u3000", " ").lower()
