from pathlib import Path

from openpyxl import Workbook

from corp_stat_autofiller.cli import (
    _month_in_filename,
    main,
    payroll_csv_months_for_basis,
    previous_quarter_months,
    resolve_payroll_csv_paths,
    resolve_statement_csv_paths,
    resolve_survey_template_path,
    statement_report_months,
    statement_months_for_file,
)


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


def test_auto_payroll_csv_paths_are_limited_to_quarter_months(tmp_path: Path, monkeypatch):
    input_dir = tmp_path / "materials" / "input"
    input_dir.mkdir(parents=True)
    (input_dir / "payroll_2026年01月25日支給.csv").write_text("", encoding="utf-8")
    (input_dir / "payroll_2026年03月25日支給.csv").write_text("", encoding="utf-8")
    (input_dir / "payroll_2026年04月25日支給.csv").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    paths = resolve_payroll_csv_paths(None, [1, 2, 3])
    target_month_set = {1, 2, 3}
    filtered = [path for path in paths if _month_in_filename(Path(path).name) in target_month_set]

    assert [Path(path).name for path in filtered] == [
        "payroll_2026年01月25日支給.csv",
        "payroll_2026年03月25日支給.csv",
    ]


def test_worked_month_payroll_uses_next_month_payment_files():
    assert payroll_csv_months_for_basis([1, 2, 3], "worked_month") == [2, 3, 4]
    assert payroll_csv_months_for_basis([1, 2, 3], "paid_month") == [1, 2, 3]


def test_survey_template_auto_detection_ignores_input_root_xlsx(tmp_path: Path, monkeypatch):
    input_dir = tmp_path / "materials" / "input"
    template_dir = input_dir / "template"
    template_dir.mkdir(parents=True)
    root_xlsx = input_dir / "法人企業統計調査_downloaded.xlsx"
    template_xlsx = template_dir / "法人企業統計調査_template.xlsx"
    root_xlsx.write_bytes(b"root")
    template_xlsx.write_bytes(b"template")
    monkeypatch.chdir(tmp_path)

    assert Path(resolve_survey_template_path(None)) == Path("materials/input/template/法人企業統計調査_template.xlsx")


def test_statement_csv_auto_detection_uses_latest_duplicate_for_same_months(tmp_path: Path, monkeypatch):
    input_dir = tmp_path / "materials" / "input"
    input_dir.mkdir(parents=True)
    older = input_dir / "損益計算書_月次推移_20260528_1342.csv"
    newer = input_dir / "損益計算書_月次推移_20260528_1353.csv"
    csv = "勘定科目,1月,2月,3月\n売上高合計,1,2,3\n"
    older.write_text(csv, encoding="utf-8")
    newer.write_text(csv, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    paths = resolve_statement_csv_paths(None, ("損益計算書", "pl"), [10, 11, 12, 1, 2, 3])

    assert [Path(path) for path in paths] == [Path("materials/input/損益計算書_月次推移_20260528_1353.csv")]


def test_statement_csv_auto_detection_keeps_distinct_month_sets(tmp_path: Path, monkeypatch):
    input_dir = tmp_path / "materials" / "input"
    input_dir.mkdir(parents=True)
    previous = input_dir / "損益計算書_月次推移_20260528_1342.csv"
    current = input_dir / "損益計算書_月次推移_20260528_1353.csv"
    previous.write_text("勘定科目,10月,11月,12月\n売上高合計,1,2,3\n", encoding="utf-8")
    current.write_text("勘定科目,1月,2月,3月\n売上高合計,4,5,6\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    paths = resolve_statement_csv_paths(None, ("損益計算書", "pl"), [10, 11, 12, 1, 2, 3])

    assert [Path(path) for path in paths] == [
        Path("materials/input/損益計算書_月次推移_20260528_1342.csv"),
        Path("materials/input/損益計算書_月次推移_20260528_1353.csv"),
    ]
    assert statement_months_for_file(paths[0], [10, 11, 12, 1, 2, 3]) == (10, 11, 12)
    assert statement_months_for_file(paths[1], [10, 11, 12, 1, 2, 3]) == (1, 2, 3)


def test_statement_csv_auto_detection_skips_non_matching_month_sets(tmp_path: Path, monkeypatch):
    input_dir = tmp_path / "materials" / "input"
    input_dir.mkdir(parents=True)
    previous = input_dir / "損益計算書_月次推移_20260604_1144.csv"
    current = input_dir / "損益計算書_月次推移_20260528_1342.csv"
    previous.write_text("勘定科目,10月,11月,12月\n売上高合計,1,2,3\n", encoding="utf-8")
    current.write_text("勘定科目,1月,2月,3月\n売上高合計,4,5,6\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    paths = resolve_statement_csv_paths(None, ("損益計算書", "pl"), [1, 2, 3])

    assert [Path(path) for path in paths] == [Path("materials/input/損益計算書_月次推移_20260528_1342.csv")]


def test_previous_quarter_months_wraps_year_boundary():
    assert previous_quarter_months([1, 2, 3]) == [10, 11, 12]
    assert previous_quarter_months([7, 8, 9]) == [4, 5, 6]


def test_statement_report_months_use_current_pl_and_opening_bs_periods():
    pl_months, bs_months = statement_report_months([1, 2, 3])

    assert pl_months == [1, 2, 3]
    assert bs_months == [10, 11, 12]
