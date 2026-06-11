# zip配布手順

このドキュメントは、社員に試用してもらうための配布zipを作る手順です。空の `materials/` フォルダ構成と調査票テンプレートはzipに入れますが、個人情報、会計データ、出力結果、仮想環境はzipに入れません。

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
- `materials/input/template/法人企業統計調査_template.xlsx`
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
- `materials/output/` 内の実行結果
- `input/`
- `output/`
- `sample_output/`
- `dist/`
- `.gitkeep`
- `*.pyc`
- `*.pyo`

`materials/` のフォルダ自体は、社員が置き場所に迷わないようzipに入れます。調査票テンプレートは `materials/input/template/` に同梱します。ただしCSV、PDF、出力結果など、個人情報や会計情報を含む可能性が高いファイルは配布zipには入れません。

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
$version = "v1.0.2"
$releaseName = "corp-stat-autofiller-$version"
$staging = "dist\$releaseName"
$zipPath = "dist\$releaseName.zip"
$templateSource = "materials\input\template\法人企業統計調査_template.xlsx"

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
Copy-Item $templateSource "$staging\materials\input\template\"

Get-ChildItem $staging -Recurse -Force |
    Where-Object {
        $_.Name -in @(".gitkeep", ".pytest_cache", "__pycache__") -or
        $_.Extension -in @(".pyc", ".pyo")
    } |
    Remove-Item -Recurse -Force

Compress-Archive -Path $staging -DestinationPath $zipPath -Force
```

`$version` を変えると、作成されるzip名とzip内のトップフォルダ名が同時に変わります。たとえば `$version = "v1.0.1"` の場合は `dist/corp-stat-autofiller-v1.0.1.zip` になり、zip内のトップフォルダも `corp-stat-autofiller-v1.0.1` になります。

## 作成後チェック

zipの中にキャッシュや `.gitkeep` が入っていないか確認します。

```powershell
$version = "v1.0.1"
$releaseName = "corp-stat-autofiller-$version"
$zipPath = "dist\$releaseName.zip"
$checkDir = "dist\_zip_check"

Remove-Item -Recurse -Force $checkDir -ErrorAction SilentlyContinue
Expand-Archive -Path $zipPath -DestinationPath $checkDir -Force

$topDirs = Get-ChildItem $checkDir -Directory
if ($topDirs.Count -ne 1 -or $topDirs[0].Name -ne $releaseName) {
    $topDirs | Select-Object Name, FullName
    throw "zip内のトップフォルダ名がバージョン名と一致していません。"
}

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

$requiredTemplate = "$checkDir\$releaseName\materials\input\template\法人企業統計調査_template.xlsx"
if (-not (Test-Path $requiredTemplate -PathType Leaf)) {
    throw "調査票テンプレートがzipに入っていません: $requiredTemplate"
}

Remove-Item -Recurse -Force $checkDir
```

## 配布zipに含まれるフォルダとテンプレート

```text
materials/
  input/
    template/
      法人企業統計調査_template.xlsx
  output/
```

社員側でフォルダを作る必要はありません。統計調査テンプレート `.xlsx` はzipに同梱済みです。CSVとPDFは `materials/input/` に置きます。

## 配布時に添える説明

最低限、以下を伝えてください。

- 実行コマンドは `uv run app.py`
- 入力ファイルは `materials/input/` に置く
- テンプレートExcelは `materials/input/template/` に同梱済み
- 出力は `materials/output/<実行時刻>/` に作られる
- 出力Excelだけでなく、`validation_report.md` と `unresolved_items.csv` も確認する

## 注意

現在のExcel書き込みは `openpyxl` を使っています。テンプレートの一部の高度な条件付き書式やデータ検証拡張は、出力時に保持できない可能性があります。入力セルへの値反映は確認済みですが、提出前には必ずテンプレートのエラーチェック表示と入力規則の挙動を人が確認してください。
