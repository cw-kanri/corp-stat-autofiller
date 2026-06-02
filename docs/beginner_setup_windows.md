# 初心者向け Windows セットアップ手順

このドキュメントは、Windows PCでこのツールを動かすための手順です。コマンドは PowerShell で実行します。

## 1. zipを展開する

配布されたzipを任意の場所に展開します。

例:

```text
C:\Users\<ユーザー名>\corp-stat-autofiller
```

以降、このフォルダを「ツールのフォルダ」と呼びます。

## 2. PowerShellを開く

1. スタートメニューで `PowerShell` を検索します。
2. PowerShellを開きます。
3. ツールのフォルダへ移動します。

```powershell
cd C:\Users\<ユーザー名>\corp-stat-autofiller
```

## 3. uvをインストールする

このツールは `uv` でPythonとライブラリを管理します。

公式ドキュメントでは、Windowsのインストール方法として以下のPowerShellコマンドが案内されています。

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

インストールが終わったら、PowerShellを一度閉じて、もう一度開きます。

確認:

```powershell
uv --version
```

バージョンが表示されればOKです。

公式ドキュメント:

- https://docs.astral.sh/uv/getting-started/installation/

## 4. 入力ファイルを置く

zipには、以下の空フォルダが最初から入っています。

```text
materials/
  input/
    template/
  output/
```

その中に、必要なファイルを置きます。

```text
materials/
  input/
    template/
      .gitkeep
      法人企業統計調査_template.xlsx
    .gitkeep
    損益計算書_月次推移_20260528_1342.csv
    貸借対照表_月次推移_20260528_1342.csv
    支給控除一覧表_2026年01月25日支給.csv
    支給控除一覧表_2026年02月25日支給.csv
    支給控除一覧表_2026年03月25日支給.csv
    参考資料.pdf
  output/
    .gitkeep
```

ファイル名の目安:

- 損益計算書CSV: `損益計算書` を含む
- 貸借対照表CSV: `貸借対照表` を含む
- 給与CSV: `支給控除` を含む
- テンプレートExcel: `materials/input/template/` に置く
- PDF: `materials/input/` に置く

## 5. 実行する

ツールのフォルダで以下を実行します。

```powershell
uv run app.py
```

初回実行時は、必要なPythonやライブラリの準備に少し時間がかかることがあります。

## 6. 出力を確認する

実行すると、以下のように時刻つきフォルダが作られます。

```text
materials/output/
  20260602_111530_123456/
```

中に以下が出ます。

- `corp_stat_filled_2026Q1.xlsx`
- `fill_plan.json`
- `input_values.json`
- `audit_log.json`
- `unresolved_items.csv`
- `validation_report.md`
- `pdf_texts.json`

まず見るもの:

1. `corp_stat_filled_2026Q1.xlsx`
2. `validation_report.md`
3. `unresolved_items.csv`

Excelだけを見て完了判断しないでください。未解決項目や検証警告が残っている可能性があります。

## 7. よくあるエラー

### `uv` が見つからない

症状:

```text
uv : 用語 'uv' は認識されません
```

対処:

1. PowerShellを閉じて開き直します。
2. `uv --version` を実行します。
3. それでもだめなら、uvのインストールをもう一度実行します。

### `必要なファイルが見つかりません`

確認:

- `materials/input/template/` に `.xlsx` があるか。
- `materials/input/` に損益計算書CSVがあるか。
- `materials/input/` に貸借対照表CSVがあるか。

### 候補ファイルが複数あると言われる

同じ種類のCSVやテンプレートが複数ある場合、自動で選べないことがあります。

対処:

- 不要なファイルを別フォルダへ移動します。
- それでも必要な場合は開発者に相談してください。

### Excelを開いたまま実行した

Excelを開いていると、`~$法人企業統計調査_template.xlsx` のような一時ファイルができます。ツールはこの一時ファイルを無視しますが、出力Excelを開いたまま再実行すると、出力先で競合する可能性があります。

対処:

- 入力テンプレートは開いたままでも基本的には大丈夫です。
- 出力Excelは閉じてから再実行してください。

### 警告が出る

以下のような警告が出ることがあります。

```text
Conditional Formatting extension is not supported and will be removed
Data Validation extension is not supported and will be removed
```

意味:

- 値の入力自体はできます。
- ただし、Excelの高度な条件付き書式や入力規則が一部保持されない可能性があります。

対処:

- 出力Excelを開き、テンプレートのエラーチェックや表示が問題ないか確認してください。

## 8. もう一度実行したいとき

そのまま同じコマンドを実行します。

```powershell
uv run app.py
```

出力は毎回別の時刻フォルダに作られるので、前回結果は上書きされません。

## 9. 入力ファイルや出力ファイルの扱い

`materials/` 配下には個人情報や会計情報が入る可能性があります。

- メールで不用意に送らない
- Gitに入れない
- 不要になった出力は削除する
- 提出前は必ず人が確認する
