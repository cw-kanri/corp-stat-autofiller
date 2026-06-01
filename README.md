# corp-stat-autofiller

法人企業統計調査（四半期別調査票B）の Excel 自動入力支援ツールです。MF会計・MF給与から出力した CSV を読み込み、外部設定ファイルに基づいて調査票セルへの入力計画を作成し、検証結果と監査ログを出力します。

この初期実装では、推測で値を埋めることよりも、トレーサビリティ、unresolved 出力、検証可能性を優先しています。

## 入力ファイル

- 調査票テンプレート xlsx
- MF会計 損益計算書 月次推移 csv
- MF会計 貸借対照表 月次推移 csv
- MF給与 支給控除一覧表 csv（複数指定可）
- `config/mapping.yaml`
- `config/rules.yaml`

PDF 読み込み用の補助モジュールはありますが、OCR は未実装です。

## 実行方法

```powershell
python app.py `
  --survey-template ".\input\survey.xlsx" `
  --pl-csv ".\input\pl.csv" `
  --bs-csv ".\input\bs.csv" `
  --payroll-csv ".\input\payroll_20260125.csv" `
  --payroll-csv ".\input\payroll_20260225.csv" `
  --payroll-csv ".\input\payroll_20260325.csv" `
  --mapping ".\config\mapping.yaml" `
  --rules ".\config\rules.yaml" `
  --quarter "2026Q1" `
  --payroll-basis "worked_month" `
  --output-dir ".\output"
```

## dry-run

Excel を保存せず、入力予定だけを確認します。

```powershell
python app.py --pl-csv ".\input\pl.csv" --bs-csv ".\input\bs.csv" --quarter "2026Q1" --dry-run --output-dir ".\output"
```

dry-run でも以下を出力します。

- `fill_plan.json`
- `input_values.json`
- `audit_log.json`
- `unresolved_items.csv`
- `validation_report.md`

## strict mode

`--strict` を付けると、unresolved が1件でもある場合、または重大な validation error がある場合に非ゼロ終了します。

```powershell
python app.py --pl-csv ".\input\pl.csv" --quarter "2026Q1" --dry-run --strict
```

## 人件費の前提

人件費は専用ロジックで集計します。`--payroll-basis` は必須の業務判断として扱い、以下のいずれかを明示してください。

- `paid_month`: 支給月ベース
- `worked_month`: 稼働月ベース

役員・従業員判定は、初期実装では CSV の役職区分・雇用区分・氏名に含まれる文字列を見ます。派遣社員は人数・給与集計から除外します。生涯設計手当や確定拠出年金などの扱いは `config/rules.yaml` の給与フィールド定義で調整してください。

## 端数処理

- 金額は円から百万円単位へ変換します。
- 原則は四捨五入です。
- 資本金は `mapping.yaml` で `rounding: floor` を指定し、百万円未満を切り捨てます。

## unresolved の見方

`unresolved_items.csv` には、値やセル番地を一意に決められなかった項目を出力します。`reason` と `candidates` を確認し、`config/mapping.yaml` または `config/rules.yaml` に業務判断を追加してください。

## 将来の API 置換方針

CSV 読み込みは `loaders/` に閉じ込めています。将来 MF API へ差し替える場合も、同じドメインモデルへ変換すれば、マッピング、検証、Excel 書き込みは再利用できます。

## 既知の未対応事項

- OCR フォールバック
- GUI
- MF会計仕訳 CSV による人件費補完
- 調査票テンプレートの実セル番地への完全追従
- 「その他」項目への差額自動調整
- リース yes/no 欄の自動判定
- 投資その他の資産内訳の詳細分解

## ディレクトリ構成

```text
app.py
config/
  mapping.yaml
  rules.yaml
sample_output/
src/corp_stat_autofiller/
  cli.py
  loaders/
  mapping/
  models/
  rules/
  writers/
tests/
```

## テスト

```powershell
pytest
```

