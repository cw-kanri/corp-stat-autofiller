from __future__ import annotations

from collections import defaultdict
from typing import Any

from corp_stat_autofiller.loaders.pl_csv_loader import StatementAmount
from corp_stat_autofiller.models import FillPlanItem, InputValue, UnresolvedItem
from corp_stat_autofiller.rules.business_rules import to_million_yen


def resolve_statement_values(
    amounts: list[StatementAmount],
    mapping: dict[str, Any],
    section: str,
) -> tuple[list[InputValue], list[UnresolvedItem]]:
    account_totals: dict[str, float] = defaultdict(float)
    account_traces: dict[str, list[str]] = defaultdict(list)
    for amount in amounts:
        normalized = _normalize(amount.account)
        account_totals[normalized] += amount.amount
        account_traces[normalized].append(amount.source)

    values: list[InputValue] = []
    unresolved: list[UnresolvedItem] = []
    for item in mapping.get(section, []):
        item_id = str(item["item_id"])
        label = str(item["label"])
        accounts = [_normalize(account) for account in item.get("accounts", [])]
        optional = bool(item.get("optional", False))
        rounding = item.get("rounding", "round")
        matched = [account for account in accounts if account in account_totals]
        if not matched and not optional:
            unresolved.append(
                UnresolvedItem(
                    item_id=item_id,
                    label=label,
                    reason="対応する勘定科目が入力CSVに見つかりません。",
                    candidates=item.get("accounts", []),
                )
            )
            continue
        raw_value = sum(account_totals[account] for account in matched)
        value = to_million_yen(raw_value, "floor" if rounding == "floor" else "round")
        trace = [trace for account in matched for trace in account_traces[account]]
        values.append(InputValue(item_id, label, value, "百万円", section, trace))
    return values, unresolved


def build_fill_plan(values: list[InputValue], mapping: dict[str, Any]) -> tuple[list[FillPlanItem], list[UnresolvedItem]]:
    cells = {str(item["item_id"]): item for item in mapping.get("cells", [])}
    default_sheet = mapping.get("default_sheet", "入力画面")
    plan: list[FillPlanItem] = []
    unresolved: list[UnresolvedItem] = []
    for value in values:
        cell_map = cells.get(value.item_id)
        if not cell_map:
            unresolved.append(
                UnresolvedItem(
                    item_id=value.item_id,
                    label=value.label,
                    reason="セル番地が mapping.yaml に定義されていません。",
                )
            )
            continue
        plan.append(
            FillPlanItem(
                item_id=value.item_id,
                label=value.label,
                sheet=cell_map.get("sheet", default_sheet),
                cell=cell_map["cell"],
                value=value.value,
                source=value.source,
                trace=value.trace,
            )
        )
    return plan, unresolved


def _normalize(value: str) -> str:
    return value.strip().replace("　", " ").lower()

