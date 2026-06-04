from pathlib import Path

from corp_stat_autofiller.loaders.payroll_csv_loader import PayrollRecord, load_payroll_records
from corp_stat_autofiller.rules.payroll_rules import resolve_payroll_values


RULES = {
    "payroll": {
        "months_in_quarter": 3,
        "fields": {
            "officer_salary": ["officer_salary"],
            "employee_salary": ["employee_salary"],
            "welfare_expense": ["welfare"],
            "officer_bonus": ["officer_bonus"],
            "employee_bonus": ["employee_bonus"],
        },
    }
}


def test_payroll_requires_basis():
    values, unresolved = resolve_payroll_values([], RULES, None)

    assert values == []
    assert unresolved[0].item_id == "payroll_basis"


def test_payroll_resolves_officer_employee_and_welfare_values():
    records = [
        PayrollRecord("1", "officer", "役員", {"officer_salary": 1_200_000, "welfare": 100_000}, "payroll.csv:1"),
        PayrollRecord("2", "employee", "正社員", {"employee_salary": 900_000, "welfare": 80_000, "employee_bonus": 500_000}, "payroll.csv:2"),
        PayrollRecord("3", "temp", "派遣", {"employee_salary": 900_000}, "payroll.csv:3"),
    ]
    values, unresolved = resolve_payroll_values(records, RULES, "paid_month")
    by_id = {value.item_id: value.value for value in values}

    assert unresolved == []
    assert by_id["54"] == 1
    assert by_id["55"] == 0
    assert by_id["56"] == 1
    assert by_id["57"] == 1
    assert by_id["58"] == 0
    assert by_id["61"] == 1


def test_payroll_loader_reads_real_japanese_headers_and_skips_total_row(tmp_path: Path):
    csv_path = tmp_path / "payroll.csv"
    csv_path.write_text(
        "従業員番号,従業員,役員報酬(支給),職能給(支給),生涯設計手当(支給),労保対象合計\n"
        "1001,officer,900000,,,0\n"
        "1002,employee,,345000,55000,390000\n"
        "合計,-,900000,345000,55000,390000\n",
        encoding="utf-8",
    )

    records = load_payroll_records([csv_path])
    values, unresolved = resolve_payroll_values(records, {"payroll": {"months_in_quarter": 3, "fields": {}}}, "paid_month")
    by_id = {value.item_id: value.value for value in values}

    assert unresolved == []
    assert len(records) == 2
    assert by_id["54"] == 1
    assert by_id["55"] == 0
    assert by_id["56"] == 1
    assert by_id["57"] == 0


def test_default_payroll_fields_exclude_life_plan_allowance_and_company_welfare():
    records = [
        PayrollRecord(
            "1",
            "employee",
            "",
            {
                "職能給(支給)": 6_732_342,
                "生涯設計手当(支給)": 1_155_000,
                "健康保険料(会社)": 554_856,
                "厚生年金保険料(会社)": 941_535,
            },
            "payroll.csv:1",
        )
    ]

    values, unresolved = resolve_payroll_values(records, {"payroll": {"months_in_quarter": 3, "fields": {}}}, "worked_month")
    by_id = {value.item_id: value.value for value in values}

    assert unresolved == []
    assert by_id["57"] == 7
    assert by_id["58"] == 0
