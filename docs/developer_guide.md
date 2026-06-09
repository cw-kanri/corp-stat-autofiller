# 開発者向けガイド

このドキュメントは、git clone 後の開発、テスト、長期的に起こりそうな問題の切り分け方をまとめたものです。

## 初期セットアップ

```powershell
git clone <repository-url>
cd corp-stat-autofiller
uv run --extra dev pytest
```

`uv run` は依存関係と仮想環境を自動で準備します。通常、手動で `.venv` を作る必要はありません。

リポジトリには空の `materials/input/`、`materials/input/template/`、`materials/output/` を `.gitkeep` で含めます。実データや実行結果はgit追跡外です。

## 実行

```powershell
uv run app.py
```

既定値は [src/corp_stat_autofiller/cli.py](../src/corp_stat_autofiller/cli.py) の `DEFAULT_RUN_CONFIG` にあります。

入力:

- `materials/input/template/*.xlsx`
- `materials/input/*.csv`
- `materials/input/*.pdf`

出力:

- `materials/output/<実行時刻>/`

## 主要モジュール

- `app.py`: 直実行入口。`src/` を import path に追加してCLIを呼びます。
- `src/corp_stat_autofiller/cli.py`: 実行設定、入力検出、処理全体の流れ。
- `loaders/`: CSV、PDF、Excelテンプレート読み込み。
- `mapping/mapping_resolver.py`: 勘定科目から調査票項目への変換。
- `rules/`: 百万円丸め、人件費、validation。
- `writers/workbook_writer.py`: Excelコピーとセル書き込み。
- `writers/audit_writer.py`: JSON、CSV、Markdown出力。
- `config/mapping.yaml`: 調査票セル番地と勘定科目マッピング。
- `config/rules.yaml`: 必須項目、検証式、人件費フィールド。

## テスト

```powershell
uv run --extra dev pytest
```

現在のテストは実データ不要です。一時CSVや一時Excelを作って検証します。

重点テスト:

- `tests/test_statement_loaders.py`: PL/BS CSV読み込み、PLは3か月合計、BSは四半期末残高。
- `tests/test_workbook_writer.py`: 結合セルに当たった場合の左上セル解決。
- `tests/test_end_to_end_dry_run.py`: end-to-end出力。
- `tests/test_mapping_resolver.py`: マッピングとunresolved。
- `tests/test_payroll_rules.py`: 人件費。
- `tests/test_validation_rules.py`: 検証式。

## よくある問題と切り分け

### `ModuleNotFoundError: No module named 'corp_stat_autofiller'`

原因:

- `src/` 配下パッケージが import path に入っていない。
- `python -c` などで直接確認スクリプトを動かしている。

対処:

- 通常実行は `uv run app.py` を使う。
- 確認スクリプトでは `sys.path.insert(0, "src")` を入れる。

### `必要なファイルが見つかりません`

確認:

- `materials/input/template/` に `.xlsx` があるか。
- `materials/input/` に `損益計算書` を含むCSVがあるか。
- `materials/input/` に `貸借対照表` を含むCSVがあるか。
- 給与CSVは `支給控除` を含むファイル名か。

テンプレートを自動検出する場合、候補にするのは `materials/input/template/*.xlsx` だけです。`materials/input/` 直下の `.xlsx` はCSV/PDF置き場との混同を避けるため、テンプレート候補にはしません。

複数候補がある場合:

- `DEFAULT_RUN_CONFIG["survey_template"]`
- `DEFAULT_RUN_CONFIG["pl_csv"]`
- `DEFAULT_RUN_CONFIG["bs_csv"]`

に明示パスを入れます。

### Excel書き込みで `MergedCell` エラー

原因:

- 書き込み先セルが結合セルの左上ではない。

現状:

- `writers/workbook_writer.py` の `resolve_writable_cell()` で左上セルへ補正しています。

再発時:

- 新しいテンプレートで結合範囲が変わったか確認します。
- `config/mapping.yaml` のセル番地が実テンプレートの入力列を指しているか確認します。

### Excelは出るが、値が違う場所に入っている

確認:

- `materials/output/<実行時刻>/fill_plan.json`
- 出力Excelの実セル
- `config/mapping.yaml`

切り分け:

1. テンプレートの `入力画面` シートで項目番号を探す。
2. 番号の右隣または近辺の入力セルを確認する。
3. `mapping.yaml` の `cells` を修正する。
4. `uv run app.py` で再実行する。

### PL / BS の値が違う

PL:

- 3か月中損益なので対象月を合計します。
- MF CSVの合計行、例 `売上高合計`、`売上原価合計`、`販売費及び一般管理費合計` を使います。

BS:

- 貸借対照表なので四半期末月の残高を使います。
- 例: `2026Q1` なら3月列。

確認箇所:

- `loaders/pl_csv_loader.py`
- `loaders/bs_csv_loader.py`
- `config/mapping.yaml`

### `validation_report.md` に警告が残る

現状では、テンプレート内の数式セルを直接 `fill_plan` に含めていないため、営業利益や経常利益などの検証がスキップされる場合があります。

改善案:

- 入力値だけでなく、テンプレート数式の結果を読んで検証する。
- または、営業利益[48]、経常利益[53]をコード側でも算出して `fill_plan` に含める。

### `openpyxl` の条件付き書式・データ検証警告

例:

```text
Conditional Formatting extension is not supported and will be removed
Data Validation extension is not supported and will be removed
```

意味:

- 入力セルへの値反映はできます。
- ただし、Excel独自の高度な条件付き書式や入力規則拡張が一部保持されない可能性があります。

長期対応:

- 完全保持が必要なら、Windows Excel COM経由で既存Excelを開き、セルだけ書き込む方式を検討します。

## 設定変更の基本方針

推測で埋めないことを優先します。

- 自信がある対応は `config/mapping.yaml` に追加。
- 人件費の扱いは `config/rules.yaml` に追加。
- 一意に決められない項目は `unresolved_items.csv` に残す。
- コードに会計判断を直接埋め込まない。

## 変更後に必ず行うこと

```powershell
uv run --extra dev pytest
uv run app.py
```

確認:

- 出力Excelに値が入っているか。
- `fill_plan.json` とExcel実セルが一致するか。
- `validation_report.md` の警告やエラーが妥当か。
- `unresolved_items.csv` に残った項目が妥当か。
