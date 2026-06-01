from __future__ import annotations

from collections import defaultdict
from typing import Any

from corp_stat_autofiller.loaders.payroll_csv_loader import PayrollRecord
from corp_stat_autofiller.models import InputValue, UnresolvedItem
from corp_stat_autofiller.rules.business_rules import to_million_yen


OFFICER_WORDS = ("役員", "取締役", "代表")
TEMP_WORDS = ("派遣",)


def resolve_payroll_values(
    records: list[PayrollRecord],
    rules: dict[str, Any],
    payroll_basis: str | None,
) -> tuple[list[InputValue], list[UnresolvedItem]]:
    if payroll_basis not in {"paid_month", "worked_month"}:
        return [], [
            UnresolvedItem(
                item_id="payroll_basis",
                label="人件費集計基準",
                reason="--payroll-basis は paid_month / worked_month のいずれかを明示してください。",
                candidates=["paid_month", "worked_month"],
            )
        ]

    payroll_rules = rules.get("payroll", {})
    fields = payroll_rules.get("fields", {})
    welfare_fields = [field.lower() for field in fields.get("welfare_expense", [])]
    officer_salary_fields = [field.lower() for field in fields.get("officer_salary", [])]
    employee_salary_fields = [field.lower() for field in fields.get("employee_salary", [])]
    officer_bonus_fields = [field.lower() for field in fields.get("officer_bonus", [])]
    employee_bonus_fields = [field.lower() for field in fields.get("employee_bonus", [])]

    officer_keys: set[str] = set()
    employee_keys: set[str] = set()
    totals: dict[str, float] = defaultdict(float)
    trace: dict[str, list[str]] = defaultdict(list)

    for record in records:
        role_text = f"{record.role} {record.employee_name}"
        is_temp = any(word in role_text for word in TEMP_WORDS)
        is_officer = any(word in role_text for word in OFFICER_WORDS)
        person_key = record.employee_id or record.employee_name
        if is_temp:
            continue
        if is_officer:
            officer_keys.add(person_key)
        else:
            employee_keys.add(person_key)

        for key, amount in record.values.items():
            normalized = key.lower()
            if normalized in welfare_fields:
                totals["welfare_expense"] += amount
                trace["welfare_expense"].append(f"{record.source}:{key}")
            if is_officer and normalized in officer_salary_fields:
                totals["officer_salary"] += amount
                trace["officer_salary"].append(f"{record.source}:{key}")
            if not is_officer and normalized in employee_salary_fields:
                totals["employee_salary"] += amount
                trace["employee_salary"].append(f"{record.source}:{key}")
            if is_officer and normalized in officer_bonus_fields:
                totals["officer_bonus"] += amount
                trace["officer_bonus"].append(f"{record.source}:{key}")
            if not is_officer and normalized in employee_bonus_fields:
                totals["employee_bonus"] += amount
                trace["employee_bonus"].append(f"{record.source}:{key}")

    employee_average = round(len(employee_keys) / max(1, payroll_rules.get("months_in_quarter", 3)), 2)
    values = [
        InputValue("54", "役員数", len(officer_keys), "人", "payroll", sorted(officer_keys)),
        InputValue("55", "従業員数", employee_average, "人", "payroll", sorted(employee_keys)),
        InputValue("56", "役員給与", to_million_yen(totals["officer_salary"]), "百万円", "payroll", trace["officer_salary"]),
        InputValue("57", "従業員給与", to_million_yen(totals["employee_salary"]), "百万円", "payroll", trace["employee_salary"]),
        InputValue("58", "福利厚生費", to_million_yen(totals["welfare_expense"]), "百万円", "payroll", trace["welfare_expense"]),
        InputValue("60", "役員賞与", to_million_yen(totals["officer_bonus"]), "百万円", "payroll", trace["officer_bonus"]),
        InputValue("61", "従業員賞与", to_million_yen(totals["employee_bonus"]), "百万円", "payroll", trace["employee_bonus"]),
    ]
    return values, []

