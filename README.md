# PySide6 Video Analysis App

PySide6 を使った動画解析アプリの開発用リポジトリです。

## セットアップ

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 起動

```powershell
.\.venv\Scripts\Activate.ps1
python -m video_analyzer
```

## 現在の画面構成

- 監視フォルダを選択し、動画ファイルの追加・更新を検出
- 検出した動画を解析結果テーブルへ 1 行ずつ追加し、解析開始時に動画ウィンドウを表示
- 解析値は後続実装用の仮置きとして表示
- テーブル内容を列名なしのタブ区切りでクリップボードへコピー
- 選択した動画をメインウィンドウとは別のサブウィンドウで表示

## 構成

- `src/video_analyzer/`: アプリ本体
- `requirements.txt`: pip で管理する Python 依存関係
- `data/`: ローカル動画などの入力データ置き場。Git 管理対象外
- `outputs/`: 解析結果などの出力先。Git 管理対象外
