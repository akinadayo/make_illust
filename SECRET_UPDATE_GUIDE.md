# シークレット更新ガイド

## 重要な変更点
NanoBanana APIからGoogle Gemini 2.5 Flash Image APIに移行しました。
既存の`nanobanana-api-key`シークレットにGoogle APIキーを保存する必要があります。

## 手順

### 1. Google Cloud ConsoleでSecret Managerを開く
```bash
# または以下のコマンドを使用
gcloud secrets versions add nanobanana-api-key --data-file=- --project=make-illust
# その後、Google APIキーを入力してCtrl+D
```

### 2. Webコンソールから更新する場合
1. [Google Cloud Console](https://console.cloud.google.com/security/secret-manager)を開く
2. プロジェクト`make-illust`を選択
3. `nanobanana-api-key`シークレットをクリック
4. 「新しいバージョンを追加」をクリック
5. Google APIキー（2025年9月に取得したもの）を貼り付け
6. 「バージョンを追加」をクリック

### 3. 確認
デプロイ後、以下のエンドポイントで確認：
- https://standing-set-backend-812480532939.asia-northeast1.run.app/api/health

`api_key_configured: true`が表示されれば成功です。

## 注意事項
- シークレット名は`nanobanana-api-key`のままですが、中身はGoogle APIキーです
- 将来的に名前を変更する場合は、`cloudbuild.yaml`の更新が必要です
- APIキーは`gemini-2.5-flash-image-preview`モデルへのアクセス権限が必要です