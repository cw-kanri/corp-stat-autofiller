from corp_stat_autofiller.models import FillPlanItem
from corp_stat_autofiller.rules.validation_rules import validate_fill_plan


def test_validation_reports_negative_not_allowed():
    plan = [FillPlanItem("45", "sales", "sheet", "B54", -1, "pl")]
    issues = validate_fill_plan(plan, {"non_negative_items": ["45"]})

    assert issues[0].code == "negative_not_allowed"


def test_validation_checks_formula_mismatch():
    plan = [
        FillPlanItem("45", "sales", "sheet", "B54", 10, "pl"),
        FillPlanItem("46", "cost", "sheet", "B55", 4, "pl"),
        FillPlanItem("47", "expense", "sheet", "B56", 3, "pl"),
        FillPlanItem("48", "operating profit", "sheet", "B57", 2, "pl"),
    ]
    issues = validate_fill_plan(
        plan,
        {"balance_checks": [{"label": "operating_profit", "left": "[48]", "right": "[45] - [46] - [47]"}]},
    )

    assert issues[0].code == "formula_mismatch"


def test_formula_only_items_are_computed_without_warning():
    plan = [
        FillPlanItem("45", "sales", "sheet", "AA34", 64, "pl"),
        FillPlanItem("46", "cost", "sheet", "AA35", 31, "pl"),
        FillPlanItem("47", "expense", "sheet", "AA36", 21, "pl"),
        FillPlanItem("49", "interest income", "sheet", "AA38", 0, "pl"),
        FillPlanItem("51", "interest expense", "sheet", "AA40", 0, "pl"),
    ]
    issues = validate_fill_plan(
        plan,
        {
            "balance_checks": [
                {"label": "operating_profit", "left": "[48]", "right": "[45] - [46] - [47]"},
                {"label": "ordinary_profit", "left": "[53]", "right": "[48] + [49] + [50] - [51] - [52]"},
            ],
            "computed_items": {
                "48": "[45] - [46] - [47]",
                "53": "[48] + [49] + [50] - [51] - [52]",
            },
            "formula_default_zero_items": ["50", "52"],
        },
    )

    assert not [issue for issue in issues if issue.code == "formula_check_skipped"]
    assert issues == []
