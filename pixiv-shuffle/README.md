# Pixiv Shuffle Viewer

フォロー中のPixiv作者の古い作品も含めてランダム表示する個人用Webアプリ。

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. リフレッシュトークンの取得

Pixiv APIはOAuth2リフレッシュトークンで認証します。

#### 方法A: gppt ツールを使う（推奨）

```bash
pip install gppt
gppt login
```

表示されたリフレッシュトークンをコピーする。

#### 方法B: 手動でブラウザキャプチャ

1. ブラウザの開発者ツール（F12）→ ネットワークタブを開く
2. `https://accounts.pixiv.net/login` にアクセスしてログイン
3. `auth/token` へのリクエストを探す
4. レスポンスの `refresh_token` をコピー

### 3. 環境変数の設定

```bash
cp .env.example .env
# .env を編集して PIXIV_REFRESH_TOKEN を設定
```

```env
PIXIV_REFRESH_TOKEN=取得したトークンをここに貼り付け
```

### 4. 起動

```bash
uvicorn main:app --host 0.0.0.0 --port 8765
```

スマホからのアクセス（Tailscale経由）:
```
http://100.x.x.x:8765
```

---

## 初回利用手順

1. サーバー起動後、ブラウザで `http://localhost:8765` を開く
2. 「バッチを今すぐ実行」ボタンを押してPixivから作品を取得（数分かかります）
3. 取得完了後、作品がランダムに表示されます

以降は毎日午前3時に自動でバッチが実行されます。

---

## Windows での常時起動

### 方法A: タスクスケジューラ

1. タスクスケジューラを開く（`taskschd.msc`）
2. 「基本タスクの作成」→ トリガー: ログオン時
3. 操作: プログラムの開始
   - プログラム: `pythonw.exe` のフルパス（例: `C:\Python311\pythonw.exe`）
   - 引数: `-m uvicorn main:app --host 0.0.0.0 --port 8765`
   - 開始場所: `C:\path\to\pixiv-shuffle`

### 方法B: バッチファイル + ショートカット

`start.bat` を作成：

```bat
@echo off
cd /d C:\path\to\pixiv-shuffle
start /B pythonw -m uvicorn main:app --host 0.0.0.0 --port 8765
```

スタートアップフォルダ（`shell:startup`）にショートカットを置く。

---

## API エンドポイント

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/api/next` | ランダムに1件返す |
| POST | `/api/seen/{work_id}` | 表示済みにマーク |
| POST | `/api/skip/{work_id}` | スキップ（seen=0維持） |
| GET | `/api/stats` | 統計情報 |
| POST | `/api/fetch/trigger` | 手動バッチ実行 |
| GET | `/api/image_proxy?url=...` | 画像プロキシ |

---

## 設定

`.env` で変更可能な項目：

| 変数 | デフォルト | 説明 |
|---|---|---|
| `PIXIV_REFRESH_TOKEN` | （必須） | Pixivリフレッシュトークン |
| `BATCH_HOUR` | `3` | バッチ実行時刻（時） |
| `BATCH_MINUTE` | `0` | バッチ実行時刻（分） |
