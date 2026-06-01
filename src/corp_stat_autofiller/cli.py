from __future__ import annotations

import argparse
from pathlib import Path

from corp_stat_autofiller.config import load_yaml, quarter_to_months
from corp_stat_autofiller.loaders.bs_csv_loader import load_bs_amounts
from corp_stat_autofiller.loaders.payroll_csv_loader import load_payroll_records
from corp_stat_autofiller.loaders.pl_csv_loader import load_pl_amounts
from corp_stat_autofiller.mapping.mapping_resolver import build_fill_plan, resolve_statement_values
from corp_stat_autofiller.models import AuditEvent, InputValue, UnresolvedItem
from corp_stat_autofiller.rules.payroll_rules import resolve_payroll_values
from corp_stat_autofiller.rules.validation_rules import validate_fill_plan
from corp_stat_autofiller.writers.audit_writer import write_outputs
from corp_stat_autofiller.writers.workbook_writer import write_workbook


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir = Path(args.output_dir)
    events = [AuditEvent("start", "法人企業統計調査 自動入力処理を開始しました。", {"quarter": args.quarter})]

    mapping = load_yaml(args.mapping)
    rules = load_yaml(args.rules)
    months = quarter_to_months(args.quarter)

    input_values: list[InputValue] = []
    unresolved: list[UnresolvedItem] = []

    if args.pl_csv:
        pl_amounts = load_pl_amounts(args.pl_csv, months)
        values, issues = resolve_statement_values(pl_amounts, mapping, "pl")
        input_values.extend(values)
        unresolved.extend(issues)
        events.append(AuditEvent("load_pl", "PL CSVを読み込みました。", {"rows": len(pl_amounts), "months": months}))

    if args.bs_csv:
        bs_amounts = load_bs_amounts(args.bs_csv, months)
        values, issues = resolve_statement_values(bs_amounts, mapping, "bs")
        input_values.extend(values)
        unresolved.extend(issues)
        events.append(AuditEvent("load_bs", "BS CSVを読み込みました。", {"rows": len(bs_amounts), "months": months}))

    if args.payroll_csv:
        records = load_payroll_records(args.payroll_csv)
        values, issues = resolve_payroll_values(records, rules, args.payroll_basis)
        input_values.extend(values)
        unresolved.extend(issues)
        events.append(AuditEvent("load_payroll", "給与 CSVを読み込みました。", {"records": len(records), "basis": args.payroll_basis}))
    elif args.payroll_basis:
        events.append(AuditEvent("skip_payroll", "給与 CSVが指定されていないため、人件費集計をスキップしました。"))

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
        events.append(AuditEvent("skip_workbook", "重大な検証エラーがあるため、Excel保存をスキップしました。"))
        write_outputs(output_dir, input_values, fill_plan, unresolved, validation_issues, events)
        return 1

    output_name = args.copy_template_name or f"corp_stat_filled_{args.quarter}.xlsx"
    write_workbook(
        template_path=args.survey_template,
        output_path=output_dir / output_name,
        plan=fill_plan,
        keep_formulas=args.keep_formulas,
    )
    events.append(AuditEvent("write_workbook", "自動入力済み調査票を保存しました。", {"path": output_name}))
    write_outputs(output_dir, input_values, fill_plan, unresolved, validation_issues, events)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="法人企業統計調査 四半期別調査票B Excel自動入力ツール")
    parser.add_argument("--survey-template", help="調査票テンプレート xlsx")
    parser.add_argument("--pl-csv", help="MF会計 損益計算書 月次推移 csv")
    parser.add_argument("--bs-csv", help="MF会計 貸借対照表 月次推移 csv")
    parser.add_argument("--payroll-csv", action="append", default=[], help="MF給与 支給控除一覧表 csv。複数指定可")
    parser.add_argument("--mapping", default="config/mapping.yaml", help="マッピング定義 YAML")
    parser.add_argument("--rules", default="config/rules.yaml", help="ルール定義 YAML")
    parser.add_argument("--quarter", required=True, help="対象四半期。例: 2026Q1")
    parser.add_argument("--payroll-basis", choices=["paid_month", "worked_month"], help="給与集計基準")
    parser.add_argument("--output-dir", default="output", help="出力ディレクトリ")
    parser.add_argument("--dry-run", action="store_true", help="Excelを保存せず fill_plan 等のみ出力")
    parser.add_argument("--strict", action="store_true", help="unresolved または重大エラーがあれば非ゼロ終了")
    parser.add_argument("--verbose", action="store_true", help="将来の詳細ログ用。現在は監査ログに集約")
    parser.add_argument("--allow-unresolved", action="store_true", help="互換用。strict未指定時はunresolvedを許容")
    parser.add_argument("--keep-formulas", action="store_true", default=True, help="数式を保持してExcelを書き込む")
    parser.add_argument("--copy-template-name", help="出力xlsx名")
    return parser

