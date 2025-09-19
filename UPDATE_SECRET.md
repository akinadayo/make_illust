# Secret Manager更新手順

## 重要: プロジェクトは `makeillust` (812480532939) を使用

現在、`nanobanana-api-key`シークレットに誤った値（15文字）が設定されています。
正しいGoogle APIキーに更新する必要があります。

## 更新方法

### 方法1: コマンドラインから
```bash
# あなたの実際のGoogle APIキー（2025年9月取得）を設定
echo -n "YOUR-ACTUAL-GOOGLE-API-KEY" | \
  gcloud secrets versions add nanobanana-api-key \
  --data-file=- \
  --project=makeillust
```

### 方法2: Google Cloud Consoleから
1. https://console.cloud.google.com/security/secret-manager にアクセス
2. プロジェクト `makeillust` を選択
3. `nanobanana-api-key` をクリック
4. 「新しいバージョンを追加」をクリック
5. Google APIキーを入力（改行なし）
6. 「バージョンを追加」をクリック

## Google APIキーの要件
- Gemini API (generativelanguage.googleapis.com) が有効
- 特に `gemini-2.5-flash-image-preview` モデルへのアクセス権限
- 通常39文字程度の長さ（例: AIzaSy...）

## 確認方法
更新後、以下で確認：
```bash
curl https://standing-set-backend-812480532939.asia-northeast1.run.app/api/health
```

`api_key_length` が39前後になっていれば成功です。

## 再デプロイ
シークレット更新後、GitHubにpushして再デプロイ：
```bash
git push origin main
```

Cloud Buildが自動的に新しいシークレットを使用してデプロイします。