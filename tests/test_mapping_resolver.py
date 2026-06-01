from corp_stat_autofiller.loaders.pl_csv_loader import StatementAmount
from corp_stat_autofiller.mapping.mapping_resolver import build_fill_plan, resolve_statement_values


def test_resolve_statement_values_uses_mapping_accounts_and_million_rounding():
    mapping = {
        "pl": [
            {"item_id": "45", "label": "売上高", "accounts": ["売上高合計"]},
        ],
        "cells": [{"item_id": "45", "label": "売上高", "cell": "B54"}],
    }
    values, unresolved = resolve_statement_values(
        [StatementAmount("売上高合計", 1_500_000, "pl.csv:売上高合計")],
        mapping,
        "pl",
    )
    plan, cell_unresolved = build_fill_plan(values, mapping)

    assert unresolved == []
    assert cell_unresolved == []
    assert values[0].value == 2
    assert plan[0].cell == "B54"


def test_required_account_without_match_becomes_unresolved():
    mapping = {
        "pl": [
            {"item_id": "46", "label": "売上原価", "accounts": ["売上原価合計"]},
        ]
    }
    values, unresolved = resolve_statement_values([], mapping, "pl")

    assert values == []
    assert unresolved[0].item_id == "46"

