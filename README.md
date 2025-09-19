# 立ち絵5表情・一括生成アプリ (Standing-Set-5)

チャット式インタビューを通じてキャラクター設定を収集し、NanoBanana APIで5つの表情差分を一括生成するアプリケーションです。

## 機能

- 🎭 チャット式インタビュー（6問＋確認2問）
- 📝 リアルタイムJSONプレビュー
- 🎨 NanoBananaによる5表情一括生成
- 🖼️ rembgによる自動背景透過
- 📦 ZIP形式でのダウンロード

## 生成される表情

1. ニュートラル（基準表情）
2. 微笑み
3. 驚き
4. 困り顔
5. むすっ

## セットアップ

### 前提条件

- Docker & Docker Compose
- NanoBanana API Key

### インストール手順

1. リポジトリをクローン
```bash
git clone <repository_url>
cd 立ち絵生成
```

2. 環境変数の設定
```bash
cp .env.example .env
# .envファイルを編集してNANOBANANA_API_KEYを設定
```

3. Dockerコンテナの起動
```bash
docker-compose up --build
```

4. アクセス
- フロントエンド: http://localhost:5173
- バックエンドAPI: http://localhost:8080
- API ドキュメント: http://localhost:8080/docs

## 開発環境での実行

### バックエンド

```bash
cd server
pip install -r requirements.txt
export NANOBANANA_API_KEY=your_api_key
uvicorn server.main:app --reload --port 8080
```

### フロントエンド

```bash
cd frontend
npm install
npm run dev
```

## Cloud Run へのデプロイ

```bash
# ビルド
gcloud builds submit --tag gcr.io/$(gcloud config get-value project)/standing-set

# デプロイ
gcloud run deploy standing-set \
  --image gcr.io/$(gcloud config get-value project)/standing-set \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars NANOBANANA_API_KEY=YOUR_KEY
```

## API エンドポイント

### POST /api/generate
キャラクターデータを送信して画像を生成

**リクエストボディ:**
```json
{
  "character": {
    "character_id": "string",
    "seed": 123456789,
    "basic": { ... },
    "hair": { ... },
    "face": { ... },
    "outfit": { ... },
    "persona": { ... }
  },
  "return_type": "zip"  // or "base64_list"
}
```

### GET /api/health
ヘルスチェック

## 技術スタック

- **バックエンド**: FastAPI, Python 3.11
- **フロントエンド**: React, Vite
- **画像処理**: NanoBanana API, rembg
- **コンテナ化**: Docker, Docker Compose

## ライセンス

[ライセンス情報を記載]