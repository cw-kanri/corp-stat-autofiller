from corp_stat_autofiller.models import FillPlanItem
from corp_stat_autofiller.rules.validation_rules import validate_fill_plan


def test_validation_reports_negative_not_allowed():
    plan = [FillPlanItem("45", "売上高", "入力画面", "B54", -1, "pl")]
    issues = validate_fill_plan(plan, {"non_negative_items": ["45"]})

    assert issues[0].code == "negative_not_allowed"


def test_validation_checks_business_formula():
    plan = [
        FillPlanItem("45", "売上高", "入力画面", "B54", 10, "pl"),
        FillPlanItem("46", "売上原価", "入力画面", "B55", 4, "pl"),
        FillPlanItem("47", "販管費", "入力画面", "B56", 3, "pl"),
        FillPlanItem("48", "営業利益", "入力画面", "B57", 2, "pl"),
    ]
    issues = validate_fill_plan(
        plan,
        {"balance_checks": [{"label": "営業利益", "left": "[48]", "right": "[45] - [46] - [47]"}]},
    )

    assert issues[0].code == "balance_mismatch"

