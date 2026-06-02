from pathlib import Path

from openpyxl import Workbook

from corp_stat_autofiller.cli import main


def test_end_to_end_dry_run_writes_plan(tmp_path: Path):
    pl = tmp_path / "pl.csv"
    bs = tmp_path / "bs.csv"
    payroll = tmp_path / "payroll.csv"
    output = tmp_path / "output"

    pl.write_text(
        "勘定科目,1月,2月,3月\n"
        "売上高合計,1000000,1000000,1000000\n"
        "売上原価合計,400000,400000,400000\n"
        "販売費及び一般管理費合計,300000,300000,300000\n",
        encoding="utf-8",
    )
    bs.write_text(
        "勘定科目,1月,2月,3月\n"
        "現金及び預金合計,1000000,1000000,1000000\n"
        "売上債権合計,500000,500000,500000\n"
        "仕入債務合計,300000,300000,300000\n"
        "資本金,10000000,10000000,10000000\n",
        encoding="utf-8",
    )
    payroll.write_text(
        "社員番号,氏名,雇用区分,基本給,健康保険料(会社)\n"
        "1,佐藤,正社員,900000,80000\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--pl-csv",
            str(pl),
            "--bs-csv",
            str(bs),
            "--payroll-csv",
            str(payroll),
            "--quarter",
            "2026Q1",
            "--payroll-basis",
            "paid_month",
            "--output-dir",
            str(output),
            "--dry-run",
        ]
    )

    assert exit_code == 0
    run_output = latest_run_output(output)
    assert (run_output / "fill_plan.json").exists()
    assert (run_output / "unresolved_items.csv").exists()
    assert (run_output / "validation_report.md").exists()


def test_end_to_end_writes_workbook_into_timestamped_dir(tmp_path: Path):
    template = tmp_path / "survey.xlsx"
    pl = tmp_path / "pl.csv"
    bs = tmp_path / "bs.csv"
    output = tmp_path / "output"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "入力画面"
    workbook.save(template)

    pl.write_text(
        "勘定科目,1月,2月,3月\n"
        "売上高合計,1000000,1000000,1000000\n"
        "売上原価合計,400000,400000,400000\n"
        "販売費及び一般管理費合計,300000,300000,300000\n",
        encoding="utf-8",
    )
    bs.write_text(
        "勘定科目,1月,2月,3月\n"
        "現金及び預金合計,1000000,1000000,1000000\n"
        "売上債権合計,500000,500000,500000\n"
        "仕入債務合計,300000,300000,300000\n"
        "資本金,10000000,10000000,10000000\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--survey-template",
            str(template),
            "--pl-csv",
            str(pl),
            "--bs-csv",
            str(bs),
            "--quarter",
            "2026Q1",
            "--output-dir",
            str(output),
        ]
    )

    run_output = latest_run_output(output)
    assert exit_code in {0, 1}
    assert (run_output / "corp_stat_filled_2026Q1.xlsx").exists()
    assert (run_output / "fill_plan.json").exists()


def latest_run_output(output: Path) -> Path:
    return max((path for path in output.iterdir() if path.is_dir()), key=lambda path: path.name)
