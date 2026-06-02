# corp-stat-autofiller

法人企業統計調査（四半期別調査票B）の Excel 自動入力支援ツールです。MF会計・MF給与から出力した CSV を読み込み、設定ファイルに基づいて調査票セルへの入力計画、検証結果、監査ログを出力します。

## いちばん簡単な実行

通常はこれだけです。

```powershell
uv run app.py
```

引数指定で毎回迷わないよう、実行設定は [src/corp_stat_autofiller/cli.py](src/corp_stat_autofiller/cli.py) の `DEFAULT_RUN_CONFIG` に入れています。

```python
DEFAULT_RUN_CONFIG = {
    "survey_template": None,
    "survey_template_pattern": "materials/input/*.xlsx",
    "pl_csv": None,
    "bs_csv": None,
    "input_csv_pattern": "materials/input/*.csv",
    "pdf_pattern": "materials/input/*.pdf",
    "quarter": "2026Q1",
    "payroll_basis": "worked_month",
    "output_dir": "materials/output",
    "dry_run": False,
}
```

初期値は `dry_run: False` なので、毎回Excelも出力します。テンプレートは `materials/input/*.xlsx` から自動検出します。複数の `.xlsx` がある場合は一意に決められないため、`DEFAULT_RUN_CONFIG["survey_template"]` に対象ファイルを明示してください。

以前 dry-run を初期値にしていた理由は、テンプレートを壊す危険ではありません。このツールはテンプレートをコピーして出力先に書くため、元ファイルは上書きしません。注意点は、未解決項目や検証エラーが残っていてもExcelが出ると「完成版」に見えやすいことです。そのため、出力Excelは必ず `validation_report.md` と `unresolved_items.csv` とセットで確認してください。

`pl_csv` と `bs_csv` が `None` の場合、`materials/input/*.csv` からファイル名で自動検出します。

- PL: `損益計算書` または `pl` を含むCSV
- BS: `貸借対照表` または `bs` を含むCSV
- 給与: `支給控除` または `payroll` を含むCSV

## 実データの置き場所

`materials/input/` 配下に置きます。`materials/` は `.gitignore` 済みなので、個人情報、会計データ、調査票、実行結果をコミットしない運用です。

```text
materials/
  input/
    template/
      法人企業統計調査_template.xlsx
    survey.xlsx
    損益計算書_月次推移_20260528_1342.csv
    貸借対照表_月次推移_20260528_1342.csv
    支給控除一覧表_2026年01月25日支給.csv
    支給控除一覧表_2026年02月25日支給.csv
    reference.pdf
```

調査票テンプレートは `materials/input/template/*.xlsx` を優先して自動検出します。Excelが開いている時にできる `~$...xlsx` の一時ファイルは無視します。PDFは `materials/input/*.pdf` を自動で拾い、本文抽出結果を `materials/output/<実行時刻>/pdf_texts.json` に出します。給与CSVがない場合は、人件費集計をスキップします。

## sample_output について

`sample_output/` も `.gitignore` 済みです。サンプルや実行結果に個人情報が混ざる可能性があるため、今後はgit追跡外のローカル確認用ディレクトリとして扱います。

## 改善サイクル

1. `materials/input/` に実データを置く
2. `DEFAULT_RUN_CONFIG` の `quarter` と `payroll_basis` を確認する
3. `uv run app.py` を実行する
4. `materials/output/<実行時刻>/corp_stat_filled_2026Q1.xlsx` で入力結果を確認する
5. `materials/output/<実行時刻>/fill_plan.json` で、どのセルに何を入れたか確認する
6. `materials/output/<実行時刻>/unresolved_items.csv` を見て、未解決項目を確認する
7. `config/mapping.yaml` に勘定科目やセル番地を追加する
8. `config/rules.yaml` に給与・検証ルールを追加する
9. テストを回す
10. もう一度 `uv run app.py` を実行する

## テスト

テストは実データ不要です。テストコード内で一時CSVを作るので、参照ファイルを事前に置く必要はありません。

```powershell
uv run --extra dev pytest
```

`pytest` がローカル環境に入っている場合は、次でも動きます。

```powershell
pytest
```

## 出力ファイル

`materials/output/` も `.gitignore` 済みです。各実行ごとに時刻フォルダを作ります。

```text
materials/output/
  20260602_111530_123456/
    corp_stat_filled_2026Q1.xlsx
    fill_plan.json
    input_values.json
    audit_log.json
    unresolved_items.csv
    validation_report.md
```

- `fill_plan.json`
- `input_values.json`
- `audit_log.json`
- `unresolved_items.csv`
- `validation_report.md`
- `pdf_texts.json`（PDFがある場合）
- `corp_stat_filled_2026Q1.xlsx`（`dry_run: False` の場合）

## 設定ファイル

- [config/mapping.yaml](config/mapping.yaml): 勘定科目から調査票項目、セル番地への対応
- [config/rules.yaml](config/rules.yaml): 必須項目、マイナス不可、人件費集計、検証式

## 人件費の前提

`payroll_basis` は以下のどちらかをコード内で明示してください。

- `paid_month`: 支給月ベース
- `worked_month`: 稼働月ベース

役員・従業員判定は、初期実装では CSV の役職区分・雇用区分・氏名に含まれる文字列を見ます。派遣社員は人数・給与集計から除外します。生涯設計手当や確定拠出年金などの扱いは `config/rules.yaml` の給与フィールド定義で調整してください。

## 既知の未対応事項

- OCR フォールバック
- GUI
- MF会計仕訳 CSV による人件費補完
- 調査票テンプレートの実セル番地への完全追従
- 「その他」項目への差額自動調整
- リース yes/no 欄の自動判定
- 投資その他の資産内訳の詳細分解
