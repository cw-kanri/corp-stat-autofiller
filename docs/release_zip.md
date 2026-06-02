# zip配布手順

このドキュメントは、社員に試用してもらうための配布zipを作る手順です。空の `materials/` フォルダ構成はzipに入れますが、個人情報、会計データ、調査票テンプレート、出力結果、仮想環境はzipに入れません。

## zipに入れるもの

必須:

- `app.py`
- `pyproject.toml`
- `uv.lock`
- `README.md`
- `.gitignore`
- `config/`
- `src/`
- `docs/`
- 空の `materials/input/`
- 空の `materials/input/template/`
- 空の `materials/output/`

任意:

- `tests/`

社員のPCで動作確認だけしてもらう場合は `tests/` は不要です。社内で改善や不具合報告もしてもらう場合は `tests/` も入れてください。

## zipに入れないもの

絶対に除外:

- `.git/`
- `.venv/`
- `.pytest_cache/`
- `__pycache__/`
- `materials/input/` 内の実ファイル
- `materials/input/template/` 内の実テンプレート
- `materials/output/` 内の実行結果
- `input/`
- `output/`
- `sample_output/`
- `dist/`
- `.gitkeep`
- `*.pyc`
- `*.pyo`

`materials/` のフォルダ自体は、社員が置き場所に迷わないようzipに入れます。ただし中身の実ファイルは個人情報や会計情報を含む可能性が高いので、配布zipには入れません。

## 配布前チェック

1. 作業ツリーを確認します。

```powershell
git status --short
```

2. テストを実行します。

```powershell
uv run --extra dev pytest
```

3. 実データで一度動かします。

```powershell
uv run app.py
```

4. 最新の `materials/output/<実行時刻>/` に以下が出ていることを確認します。

- `corp_stat_filled_2026Q1.xlsx`
- `fill_plan.json`
- `input_values.json`
- `audit_log.json`
- `unresolved_items.csv`
- `validation_report.md`

5. `validation_report.md` と `unresolved_items.csv` を確認します。

## PowerShellでzipを作る

リポジトリ直下で実行します。

```powershell
$version = "v1.0.0"
$releaseName = "corp-stat-autofiller-$version"
$staging = "dist\$releaseName"
$zipPath = "dist\$releaseName.zip"

Remove-Item -Recurse -Force "dist" -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $staging | Out-Null

Copy-Item "app.py" $staging
Copy-Item "pyproject.toml" $staging
Copy-Item "uv.lock" $staging
Copy-Item "README.md" $staging
Copy-Item ".gitignore" $staging
Copy-Item -Recurse "config" $staging
Copy-Item -Recurse "src" $staging
Copy-Item -Recurse "docs" $staging

# テストも同梱する場合だけ、次の行のコメントを外します。
# Copy-Item -Recurse "tests" $staging

New-Item -ItemType Directory -Force "$staging\materials\input\template" | Out-Null
New-Item -ItemType Directory -Force "$staging\materials\output" | Out-Null

Get-ChildItem $staging -Recurse -Force |
    Where-Object {
        $_.Name -in @(".gitkeep", ".pytest_cache", "__pycache__") -or
        $_.Extension -in @(".pyc", ".pyo")
    } |
    Remove-Item -Recurse -Force

Compress-Archive -Path $staging -DestinationPath $zipPath -Force
```

`$version` を変えると、作成されるzip名も変わります。たとえば `$version = "v1.0.0"` の場合は `dist/corp-stat-autofiller-v1.0.0.zip` になります。

## 作成後チェック

zipの中にキャッシュや `.gitkeep` が入っていないか確認します。

```powershell
$version = "v1.0.0"
$releaseName = "corp-stat-autofiller-$version"
$zipPath = "dist\$releaseName.zip"
$checkDir = "dist\_zip_check"

Remove-Item -Recurse -Force $checkDir -ErrorAction SilentlyContinue
Expand-Archive -Path $zipPath -DestinationPath $checkDir -Force

$unexpected = Get-ChildItem $checkDir -Recurse -Force |
    Where-Object {
        $_.Name -in @(".git", ".venv", ".pytest_cache", "__pycache__", ".gitkeep") -or
        $_.FullName -like "*\sample_output\*" -or
        $_.Extension -in @(".pyc", ".pyo")
    }

if ($unexpected) {
    $unexpected | Select-Object FullName
    throw "配布zipに入れてはいけないファイルがあります。"
}

$requiredDirs = @(
    "$checkDir\$releaseName\materials\input",
    "$checkDir\$releaseName\materials\input\template",
    "$checkDir\$releaseName\materials\output"
)

foreach ($dir in $requiredDirs) {
    if (-not (Test-Path $dir -PathType Container)) {
        throw "必要な空フォルダがzipに入っていません: $dir"
    }
}

Remove-Item -Recurse -Force $checkDir
```

## 配布zipに含まれる空フォルダ

```text
materials/
  input/
    template/
  output/
```

社員側でフォルダを作る必要はありません。`materials/input/template/` に統計調査テンプレート `.xlsx` を置きます。CSVとPDFは `materials/input/` に置きます。

## 配布時に添える説明

最低限、以下を伝えてください。

- 実行コマンドは `uv run app.py`
- 入力ファイルは `materials/input/` に置く
- テンプレートExcelは `materials/input/template/` に置く
- 出力は `materials/output/<実行時刻>/` に作られる
- 出力Excelだけでなく、`validation_report.md` と `unresolved_items.csv` も確認する

## 注意

現在のExcel書き込みは `openpyxl` を使っています。テンプレートの一部の高度な条件付き書式やデータ検証拡張は、出力時に保持できない可能性があります。入力セルへの値反映は確認済みですが、提出前には必ずテンプレートのエラーチェック表示と入力規則の挙動を人が確認してください。
