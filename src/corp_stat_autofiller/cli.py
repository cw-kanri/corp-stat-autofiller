from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

from corp_stat_autofiller.config import load_yaml, quarter_to_months
from corp_stat_autofiller.loaders.bs_csv_loader import load_bs_amounts
from corp_stat_autofiller.loaders.payroll_csv_loader import load_payroll_records
from corp_stat_autofiller.loaders.pdf_loader import extract_pdf_text
from corp_stat_autofiller.loaders.pl_csv_loader import load_pl_amounts
from corp_stat_autofiller.mapping.mapping_resolver import build_fill_plan, resolve_statement_values
from corp_stat_autofiller.models import AuditEvent, InputValue, UnresolvedItem
from corp_stat_autofiller.rules.payroll_rules import resolve_payroll_values
from corp_stat_autofiller.rules.validation_rules import validate_fill_plan
from corp_stat_autofiller.writers.audit_writer import write_outputs
from corp_stat_autofiller.writers.workbook_writer import write_workbook


DEFAULT_RUN_CONFIG = {
    "survey_template": None,
    "survey_template_patterns": ["materials/input/template/*.xlsx"],
    "pl_csv": None,
    "bs_csv": None,
    "input_csv_pattern": "materials/input/*.csv",
    "pdf_pattern": "materials/input/*.pdf",
    "mapping": "config/mapping.yaml",
    "rules": "config/rules.yaml",
    "quarter": "2026Q1",
    "payroll_basis": "worked_month",
    "output_dir": "materials/output",
    "dry_run": False,
    "strict": False,
    "keep_formulas": True,
    "copy_template_name": None,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    months = quarter_to_months(args.quarter)
    pl_months, bs_months = statement_report_months(months)
    payroll_months = payroll_csv_months_for_basis(months, args.payroll_basis)
    payroll_csv_was_explicit = args.payroll_csv is not None
    args.survey_template = resolve_survey_template_path(args.survey_template)
    args.pl_csv = resolve_statement_csv_paths(args.pl_csv, ("損益計算書", "pl"), pl_months)
    args.bs_csv = resolve_statement_csv_paths(args.bs_csv, ("貸借対照表", "bs"), bs_months)
    args.payroll_csv = resolve_payroll_csv_paths(args.payroll_csv, payroll_months)
    if not payroll_csv_was_explicit:
        target_month_set = set(payroll_months)
        args.payroll_csv = [
            path for path in args.payroll_csv if _month_in_filename(Path(path).name) in target_month_set
        ]
    args.pdf = resolve_pdf_paths(args.pdf)
    output_dir = create_run_output_dir(args.output_dir)
    events = [
        AuditEvent(
            "start",
            "法人企業統計調査 自動入力処理を開始しました。",
            {"quarter": args.quarter, "output_dir": str(output_dir)},
        )
    ]

    mapping = load_yaml(args.mapping)
    rules = load_yaml(args.rules)
    input_values: list[InputValue] = []
    unresolved: list[UnresolvedItem] = []

    if args.pl_csv:
        pl_amounts = [
            amount
            for path in args.pl_csv
            for amount in load_pl_amounts(
                require_existing_file(path, "PL CSV"),
                statement_months_for_file(path, pl_months),
            )
        ]
        values, issues = resolve_statement_values(pl_amounts, mapping, "pl")
        input_values.extend(values)
        unresolved.extend(issues)
        events.append(
            AuditEvent(
                "load_pl",
                "PL CSVを読み込みました。",
                {"rows": len(pl_amounts), "months": pl_months, "files": args.pl_csv},
            )
        )

    if args.bs_csv:
        bs_amounts = [
            amount
            for path in args.bs_csv
            for amount in load_bs_amounts(
                require_existing_file(path, "BS CSV"),
                statement_months_for_file(path, bs_months),
            )
        ]
        values, issues = resolve_statement_values(bs_amounts, mapping, "bs")
        input_values.extend(values)
        unresolved.extend(issues)
        events.append(
            AuditEvent(
                "load_bs",
                "BS CSVを読み込みました。",
                {"rows": len(bs_amounts), "months": bs_months, "files": args.bs_csv},
            )
        )

    if args.payroll_csv:
        records = load_payroll_records(args.payroll_csv)
        values, issues = resolve_payroll_values(records, rules, args.payroll_basis)
        input_values.extend(values)
        unresolved.extend(issues)
        events.append(AuditEvent("load_payroll", "給与 CSVを読み込みました。", {"records": len(records), "basis": args.payroll_basis}))
    elif args.payroll_basis:
        events.append(AuditEvent("skip_payroll", "給与 CSVが指定されていないため、人件費集計をスキップしました。"))

    if args.pdf:
        pdf_texts = extract_pdf_texts(args.pdf)
        write_pdf_texts(output_dir, pdf_texts)
        events.append(
            AuditEvent(
                "load_pdf",
                "PDF本文を抽出しました。",
                {"files": list(pdf_texts.keys()), "total_chars": sum(len(text) for text in pdf_texts.values())},
            )
        )

    fill_plan, cell_unresolved = build_fill_plan(input_values, mapping)
    unresolved.extend(cell_unresolved)
    validation_issues = validate_fill_plan(fill_plan, rules)
    write_outputs(output_dir, input_values, fill_plan, unresolved, validation_issues, events)

    has_error = any(issue.severity == "error" for issue in validation_issues)
    if args.strict and (unresolved or has_error):
        return 2

    if args.dry_run:
        return 0

    if has_error:
        events.append(AuditEvent("validation_error", "重大な検証エラーがありますが、確認用Excelは出力します。"))

    output_name = args.copy_template_name or f"corp_stat_filled_{args.quarter}.xlsx"
    write_workbook(
        template_path=require_existing_file(args.survey_template, "調査票テンプレート"),
        output_path=output_dir / output_name,
        plan=fill_plan,
        keep_formulas=args.keep_formulas,
    )
    events.append(AuditEvent("write_workbook", "自動入力済み調査票を保存しました。", {"path": output_name}))
    write_outputs(output_dir, input_values, fill_plan, unresolved, validation_issues, events)
    return 1 if has_error else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="法人企業統計調査 四半期別調査票B Excel自動入力ツール")
    parser.add_argument("--survey-template", default=DEFAULT_RUN_CONFIG["survey_template"], help="調査票テンプレート xlsx")
    parser.add_argument("--pl-csv", default=DEFAULT_RUN_CONFIG["pl_csv"], help="MF会計 損益計算書 月次推移 csv")
    parser.add_argument("--bs-csv", default=DEFAULT_RUN_CONFIG["bs_csv"], help="MF会計 貸借対照表 月次推移 csv")
    parser.add_argument("--payroll-csv", action="append", default=None, help="MF給与 支給控除一覧表 csv。複数指定可")
    parser.add_argument("--pdf", action="append", default=None, help="補助参照用PDF。複数指定可")
    parser.add_argument("--mapping", default=DEFAULT_RUN_CONFIG["mapping"], help="マッピング定義 YAML")
    parser.add_argument("--rules", default=DEFAULT_RUN_CONFIG["rules"], help="ルール定義 YAML")
    parser.add_argument("--quarter", default=DEFAULT_RUN_CONFIG["quarter"], help="対象四半期。例: 2026Q1")
    parser.add_argument("--payroll-basis", default=DEFAULT_RUN_CONFIG["payroll_basis"], choices=["paid_month", "worked_month"], help="給与集計基準")
    parser.add_argument("--output-dir", default=DEFAULT_RUN_CONFIG["output_dir"], help="出力ディレクトリ")
    parser.add_argument("--dry-run", action="store_true", default=DEFAULT_RUN_CONFIG["dry_run"], help="Excelを保存せず fill_plan 等のみ出力")
    parser.add_argument("--strict", action="store_true", default=DEFAULT_RUN_CONFIG["strict"], help="unresolved または重大エラーがあれば非ゼロ終了")
    parser.add_argument("--verbose", action="store_true", help="将来の詳細ログ用。現在は監査ログに集約")
    parser.add_argument("--allow-unresolved", action="store_true", help="互換用。strict未指定時はunresolvedを許容")
    parser.add_argument("--keep-formulas", action="store_true", default=DEFAULT_RUN_CONFIG["keep_formulas"], help="数式を保持してExcelを書き込む")
    parser.add_argument("--copy-template-name", default=DEFAULT_RUN_CONFIG["copy_template_name"], help="出力xlsx名")
    return parser


def resolve_payroll_csv_paths(paths: list[str] | None, target_months: list[int] | None = None) -> list[str]:
    if paths is not None:
        return paths
    return [
        str(path)
        for path in sorted(Path().glob(DEFAULT_RUN_CONFIG["input_csv_pattern"]))
        if any(keyword in path.name.lower() for keyword in ("支給控除", "payroll"))
    ]


def payroll_csv_months_for_basis(months: list[int], payroll_basis: str | None) -> list[int]:
    if payroll_basis != "worked_month":
        return months
    return [month % 12 + 1 for month in months]


def previous_quarter_months(months: list[int]) -> list[int]:
    return [month - 3 if month > 3 else month + 9 for month in months]


def statement_report_months(months: list[int]) -> tuple[list[int], list[int]]:
    return months, previous_quarter_months(months)


def _month_in_filename(name: str) -> int | None:
    match = re.search(r"\d{4}\D+(\d{1,2})\D+", name)
    if not match:
        return None
    month = int(match.group(1))
    return month if 1 <= month <= 12 else None


def resolve_survey_template_path(path: str | None) -> str | None:
    if path:
        return path
    all_candidates = find_candidate_files(DEFAULT_RUN_CONFIG["survey_template_patterns"])
    candidates = [
        candidate
        for candidate in all_candidates
        if any(keyword in candidate.name.lower() for keyword in ("調査票", "survey", "法人企業統計"))
    ]
    if not candidates:
        candidates = all_candidates
    if not candidates:
        return None
    if len(candidates) > 1:
        names = ", ".join(str(candidate) for candidate in candidates)
        raise FileNotFoundError(
            f"候補の調査票テンプレートが複数あり、一意に決められません。DEFAULT_RUN_CONFIG または引数で明示してください: {names}"
        )
    return str(candidates[0])


def find_candidate_files(patterns: list[str]) -> list[Path]:
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(Path().glob(pattern))
    return sorted(path for path in candidates if not path.name.startswith("~$"))


def resolve_statement_csv_paths(path: str | None, keywords: tuple[str, ...], report_months: list[int]) -> list[str]:
    if path:
        return [path]
    candidates = [
        candidate
        for candidate in sorted(Path().glob(DEFAULT_RUN_CONFIG["input_csv_pattern"]))
        if any(keyword.lower() in candidate.name.lower() for keyword in keywords)
    ]
    if not candidates:
        return []
    grouped: dict[tuple[int, ...], list[Path]] = {}
    for candidate in candidates:
        present_months = detect_month_columns(candidate)
        if present_months and not any(month in present_months for month in report_months):
            continue
        grouped.setdefault(statement_months_for_file(candidate, report_months), []).append(candidate)
    return [str(select_latest_candidate(group)) for group in grouped.values()]


def statement_months_for_file(path: str | Path, report_months: list[int]) -> tuple[int, ...]:
    present_months = detect_month_columns(path)
    matched = tuple(month for month in report_months if month in present_months)
    return matched or tuple(report_months)


def detect_month_columns(path: str | Path) -> set[int]:
    from corp_stat_autofiller.loaders.csv_utils import read_csv_rows
    from corp_stat_autofiller.loaders.pl_csv_loader import MONTH_COLUMNS

    try:
        rows = read_csv_rows(path)
    except (OSError, ValueError):
        return set()
    keys = set(rows[0]) if rows else set()
    return {
        month
        for month, columns in MONTH_COLUMNS.items()
        if any(column.lower() in keys for column in columns)
    }


def select_latest_candidate(candidates: list[Path]) -> Path:
    return max(candidates, key=candidate_recency_key)


def candidate_recency_key(path: Path) -> tuple[int, int, str]:
    match = re.search(r"(20\d{2})(\d{2})(\d{2})(?:[_-]?(\d{4}))?", path.stem)
    if match:
        year, month, day, time = match.groups()
        return (2, int(f"{year}{month}{day}{time or '0000'}"), path.name)
    try:
        return (1, int(path.stat().st_mtime), path.name)
    except OSError:
        return (0, 0, path.name)


def resolve_pdf_paths(paths: list[str] | None) -> list[str]:
    if paths is not None:
        return paths
    return [str(path) for path in sorted(Path().glob(DEFAULT_RUN_CONFIG["pdf_pattern"]))]


def extract_pdf_texts(paths: list[str]) -> dict[str, str]:
    texts: dict[str, str] = {}
    for path in paths:
        pdf_path = require_existing_file(path)
        texts[str(pdf_path)] = extract_pdf_text(pdf_path)
    return texts


def write_pdf_texts(output_dir: str | Path, pdf_texts: dict[str, str]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "pdf_texts.json").write_text(json.dumps(pdf_texts, ensure_ascii=False, indent=2), encoding="utf-8")


def create_run_output_dir(base_output_dir: str | Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output_dir = Path(base_output_dir) / timestamp
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def require_existing_file(path: str | Path | None, label: str = "必要ファイル") -> Path:
    if not path:
        raise FileNotFoundError(
            f"{label}が見つかりません。materials/input/ に対象ファイルを置くか、DEFAULT_RUN_CONFIG を確認してください。"
        )
    candidate = Path(path)
    if not candidate.exists():
        raise FileNotFoundError(f"{label}が見つかりません: {candidate}")
    return candidate
