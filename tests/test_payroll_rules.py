from corp_stat_autofiller.loaders.payroll_csv_loader import PayrollRecord
from corp_stat_autofiller.rules.payroll_rules import resolve_payroll_values


RULES = {
    "payroll": {
        "months_in_quarter": 3,
        "fields": {
            "officer_salary": ["役員報酬"],
            "employee_salary": ["基本給"],
            "welfare_expense": ["健康保険料(会社)"],
            "officer_bonus": ["役員賞与"],
            "employee_bonus": ["賞与"],
        },
    }
}


def test_payroll_requires_basis():
    values, unresolved = resolve_payroll_values([], RULES, None)

    assert values == []
    assert unresolved[0].item_id == "payroll_basis"


def test_payroll_resolves_officer_employee_and_welfare_values():
    records = [
        PayrollRecord("1", "山田", "役員", {"役員報酬": 1_200_000, "健康保険料(会社)": 100_000}, "payroll.csv:1"),
        PayrollRecord("2", "佐藤", "正社員", {"基本給": 900_000, "健康保険料(会社)": 80_000, "賞与": 500_000}, "payroll.csv:2"),
        PayrollRecord("3", "派遣 太郎", "派遣", {"基本給": 900_000}, "payroll.csv:3"),
    ]
    values, unresolved = resolve_payroll_values(records, RULES, "paid_month")
    by_id = {value.item_id: value.value for value in values}

    assert unresolved == []
    assert by_id["54"] == 1
    assert by_id["55"] == 0.33
    assert by_id["56"] == 1
    assert by_id["57"] == 1
    assert by_id["58"] == 0
    assert by_id["61"] == 1

