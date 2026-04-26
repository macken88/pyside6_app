# AGENTS.md

このリポジトリは PySide6 を使った動画解析デスクトップアプリです。今後の Codex/エージェント作業では、このファイルの内容を優先して参照してください。

## ルール

- 新しい skill を追加する場合、作成先は作業リポジトリ内の `.agents/skills/` に統一する。
- 既存 skill の参照先も作業リポジトリ内の `.agents/skills/` とする。
- Python ライブラリのインストールは `pip` を使う。
- 生成物、ローカルデータ、動画ファイル、解析結果は Git 管理に含めない。
- 既存の未コミット変更はユーザー作業の可能性があるため、明示指示なしに戻さない。

## プロジェクト概要

- アプリ本体は `src/video_analyzer/` に置く。
- エントリーポイントは `python -m video_analyzer`。
- 監視フォルダに動画が追加または更新されたタイミングで、解析開始扱いにする。
- 解析結果はメイン画面の表に 1 動画 1 行で蓄積する。
- 解析結果のコピーは、表頭を含めずタブ区切りでクリップボードへ送る。
- 動画表示はメインウィンドウとは別のサブウィンドウで行う。
- 動画表示ウィンドウは 1 つだけ開き、次の動画解析時は同じウィンドウの表示動画を切り替えて自動再生する。
- 監視フォルダは `QSettings` で保存し、次回起動時に選択済み状態へ復元する。
- 監視中と監視停止中は UI から切り替えられるようにする。
- メインウィンドウを閉じたら動画ウィンドウも閉じる。

## 開発環境

Python は 3.12 以上を前提にする。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

起動:

```powershell
.\.venv\Scripts\Activate.ps1
python -m video_analyzer
```

## 主要依存関係

- `PySide6`: UI と動画表示
- `opencv-python`: 今後の動画解析処理用
- `numpy`: 今後の解析処理用

## Git 管理方針

- `data/` は監視用動画などのローカル入力置き場として使い、Git 管理しない。
- `outputs/` は解析結果などのローカル出力先として使い、Git 管理しない。
- `.venv/`、`*.egg-info/`、各種 cache は Git 管理しない。
- 機能追加は原則 feature ブランチ上で行い、まとまった単位でコミットする。

## 動作確認

最低限、変更後は以下を確認する。

```powershell
.\.venv\Scripts\python.exe -m compileall src
```

PySide6 の画面起動や監視挙動を自動確認する場合は、必要に応じて `QT_QPA_PLATFORM=offscreen` を使う。空の `.mp4` を使った検証では FFmpeg の警告が出ることがあるが、これはファイル内容が実動画ではないため。

## 実装メモ

- 現在の UI は [src/video_analyzer/app.py](src/video_analyzer/app.py) にまとまっている。
- `MainWindow` は監視フォルダ、結果テーブル、監視開始/停止、コピー、クリア、動画ウィンドウの管理を持つ。
- `VideoWindow` は `QMediaPlayer`、`QVideoWidget`、再生位置スライダーを持つ。
- 解析ロジックはまだ仮実装で、結果列の値は後続実装で置き換える。
