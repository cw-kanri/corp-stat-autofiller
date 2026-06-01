from pathlib import Path

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
    assert (output / "fill_plan.json").exists()
    assert (output / "unresolved_items.csv").exists()
    assert (output / "validation_report.md").exists()

