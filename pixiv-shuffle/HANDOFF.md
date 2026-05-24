# Pixiv Shuffle Viewer — エージェント引き継ぎ資料

## リポジトリ情報

- **GitHub**: `yutaro-kuwajima/test`
- **開発ブランチ**: `claude/festive-cerf-RXDfX`
- **プロジェクトディレクトリ**: `pixiv-shuffle/`（リポジトリルート直下）
- **ユーザーのローカルパス**: `C:\Users\ykcha\claudeCode\test\pixiv-shuffle`

---

## プロジェクト概要

フォロー中のPixiv作者の古い作品も含めてランダム表示するパーソナル閲覧Webアプリ。

- **利用者**: 一人（個人利用）
- **アクセス**: スマホ → 同一Wi-Fi経由でWindows PCにアクセス（Tailscaleは不使用）
- **R-18**: 対応（Pixivアカウント設定に準ずる）

---

## 技術スタック

| 役割 | 技術 |
|---|---|
| Pixiv API | pixivpy3 |
| バックエンド | FastAPI (Python 3.11) |
| DB | SQLite（sqlite3直接、SQLAlchemyなし） |
| フロントエンド | HTML + Vanilla JS（FastAPI静的配信） |
| スケジューラ | APScheduler（FastAPI内組み込み） |

---

## ファイル構成

```
pixiv-shuffle/
├── main.py              # FastAPIアプリ本体
├── pixiv_client.py      # pixivpy3ラッパー
├── database.py          # SQLite CRUD
├── scheduler.py         # バッチ処理 + 進捗状態管理
├── config.py            # 設定値（.envロード）
├── static/
│   └── index.html       # フロントエンド（単一ファイル）
├── data/
│   └── pixiv.db         # SQLiteファイル（初回起動時に自動生成）
├── .env                 # PIXIV_REFRESH_TOKEN（gitignore対象）
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 実装済み機能

### バックエンド（`main.py`）

| エンドポイント | 説明 |
|---|---|
| `GET /` | `index.html` を返す |
| `GET /api/next?exclude_author=ID` | ランダムに1件返す（作者連続回避付き） |
| `POST /api/seen/{work_id}` | 表示済みにマーク |
| `POST /api/skip/{work_id}` | スキップ（seen=0維持、last_shown_atを更新） |
| `GET /api/stats` | 未表示件数・総件数・作者数 |
| `POST /api/fetch/trigger` | 手動バッチ実行（BackgroundTasks） |
| `GET /api/fetch/status` | バッチ進捗状態を返す |
| `GET /api/image_proxy?url=...` | Pixiv画像プロキシ（Refererヘッダー付与） |

### ランダム表示ロジック（`database.py` `get_random_work`）

- 70%: `seen=0`（未表示）の作品
- 25%: `last_shown_at` が30日以上前（または seen=1 で未表示日時なし）
- 5%: 全件からランダム
- フォールバック: 上記で0件なら全件から選ぶ

### バッチ処理（`scheduler.py`）

- 毎日03:00に自動実行（APScheduler）
- フォロー中ユーザーを全取得 → DB差分追加
- 各作者の作品を最大100件取得（offset ループ）
- 1バッチで最大50作者まで（`fetched_at` が古い順）
- 作者間1.5秒sleep
- 進捗状態をモジュールグローバル変数 `_progress` で管理

### フロントエンド（`static/index.html`）

- ダークテーマ・スマホ縦持ち最適化（max-width: 480px）
- 「スキップ」「見た！」ボタン
- 統計表示（未表示件数・総作品・作者数）
- バッチ実行中：画面上部に緑の進捗バナー（2秒ポーリング）
- バッチ完了時：バナー消去＋統計・作品を自動更新
- 作品0件時：バッチ実行促進メッセージ＋ボタン表示

---

## 修正済みバグ履歴

| コミット | 内容 |
|---|---|
| `60cd795` | `data/` ディレクトリが存在しない場合 `init_db()` がクラッシュ → `os.makedirs` 追加 |
| `fb649c5` | 無効なリフレッシュトークンで起動がクラッシュ → try/except でwarn扱いに |
| `4ed87ab` | `user_following` に `user_id="0"` を渡すと Invalid request → `api.user_id` を使用 |
| `ac3bedd` | `api.no_auth_requests_handler` が存在しない → `next_url` からoffsetをパースして再呼び出しに変更 |

---

## 現在の状況（引き継ぎ時点）

- サーバーは起動・動作確認済み
- フォロー取得のバグ修正後、**バッチが正常に完了するかは未確認**
- ユーザーは `git pull` → 再起動 → バッチ実行 を試みている最中

---

## 既知の潜在的問題点

1. **`fetch_user_illusts` のoffset更新**: `next_url` が存在しない場合のフォールバックを `offset + len(illusts)` にしているが、pixivpy3が返す実際のページサイズと一致しない可能性がある（通常30件）
2. **R-18作品の取得**: `user_illusts` に `filter="for_ios"` を渡していない。アカウント側でR-18が有効でも取得できない可能性がある
3. **バッチの二重起動防止**: `_progress["running"]` チェックはあるが、スレッドセーフではない（個人利用なので実害はほぼない）

---

## 起動方法

```bat
cd C:\Users\ykcha\claudeCode\test\pixiv-shuffle
uvicorn main:app --host 0.0.0.0 --port 8765
```

`.env` に `PIXIV_REFRESH_TOKEN=...` が必要。

---

## requirements.txt

```
fastapi
uvicorn[standard]
pixivpy3
apscheduler
python-dotenv
httpx
```
