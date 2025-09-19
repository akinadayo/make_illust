# Cloud Run GUI デプロイガイド

## 📋 前提条件
- Google Cloud アカウント
- プロジェクトの作成済み
- 課金の有効化
- NanoBanana API Key の取得済み

## 🚀 手順1: Google Cloud Console での初期設定

### 1.1 APIの有効化
1. [Google Cloud Console](https://console.cloud.google.com) にアクセス
2. 左メニュー → 「APIとサービス」→「ライブラリ」
3. 以下のAPIを検索して有効化:
   - **Cloud Run API**
   - **Cloud Build API**
   - **Container Registry API**
   - **Artifact Registry API**

### 1.2 プロジェクトIDの確認
1. コンソール上部のプロジェクト名をクリック
2. プロジェクトIDをメモ（例: `my-project-123456`）

## 🏗️ 手順2: Cloud Build でイメージをビルド

### 2.1 Cloud Build の設定
1. 左メニュー → 「Cloud Build」→「トリガー」
2. 「トリガーを作成」をクリック

### 2.2 GitHub連携（オプション）
GitHubリポジトリがある場合:
1. 「リポジトリを接続」
2. GitHubを選択して認証
3. リポジトリを選択

### 2.3 手動ビルド（推奨）
1. 左メニュー → 「Cloud Build」→「履歴」
2. 画面上部の「BUILD」ボタンをクリック
3. 「Cloud Build構成ファイル」を選択
4. 以下の内容を入力:

```yaml
steps:
  # バックエンドのビルド
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/standing-set-backend', '-f', 'Dockerfile.production', '.']
    
  # フロントエンドのビルド  
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/standing-set-frontend', '-f', 'frontend/Dockerfile.production', './frontend']

images:
  - 'gcr.io/$PROJECT_ID/standing-set-backend'
  - 'gcr.io/$PROJECT_ID/standing-set-frontend'
```

5. 「ビルドを実行」をクリック

## 🎯 手順3: Cloud Run へのデプロイ

### 3.1 バックエンドのデプロイ

1. 左メニュー → 「Cloud Run」
2. 「サービスを作成」をクリック
3. 以下を設定:

#### コンテナイメージ
- 「コンテナ イメージ URL」の「選択」をクリック
- **Container Registry** → プロジェクト → `standing-set-backend` を選択

#### サービス設定
- **サービス名**: `standing-set-backend`
- **リージョン**: `asia-northeast1`（東京）

#### 認証
- ✅ 「未認証の呼び出しを許可」を選択

#### コンテナ、ネットワーキング、セキュリティ
「コンテナ、ネットワーキング、セキュリティ」を展開:

##### コンテナタブ
- **メモリ**: `2 GiB`
- **CPU**: `2`
- **実行タイムアウト**: `300`
- **最大同時リクエスト数**: `100`
- **コンテナポート**: `8080`

##### 変数とシークレットタブ
環境変数を追加:
- **名前**: `NANOBANANA_API_KEY`
- **値**: あなたのAPIキー
- **名前**: `PORT`
- **値**: `8080`

##### 接続タブ
- **最小インスタンス数**: `0`
- **最大インスタンス数**: `10`

4. 「作成」をクリック

### 3.2 フロントエンドのデプロイ

1. 「サービスを作成」をクリック
2. 以下を設定:

#### コンテナイメージ
- `standing-set-frontend` を選択

#### サービス設定
- **サービス名**: `standing-set-frontend`
- **リージョン**: `asia-northeast1`

#### 認証
- ✅ 「未認証の呼び出しを許可」を選択

#### コンテナ、ネットワーキング、セキュリティ

##### コンテナタブ
- **メモリ**: `512 MiB`
- **CPU**: `1`
- **コンテナポート**: `80`

##### 変数とシークレットタブ
環境変数を追加:
- **名前**: `VITE_API_URL`
- **値**: バックエンドのURL（デプロイ後に取得）

3. 「作成」をクリック

## 🔗 手順4: URLの設定

### 4.1 バックエンドURLの取得
1. Cloud Run → `standing-set-backend` サービスをクリック
2. 上部に表示されるURLをコピー（例: `https://standing-set-backend-xxxxx-an.a.run.app`）

### 4.2 フロントエンドの環境変数を更新
1. Cloud Run → `standing-set-frontend` サービスをクリック
2. 「新しいリビジョンの編集とデプロイ」をクリック
3. 「コンテナ、ネットワーキング、セキュリティ」を展開
4. 環境変数 `VITE_API_URL` をバックエンドのURLに更新
5. 「デプロイ」をクリック

## ✅ 手順5: 動作確認

1. フロントエンドのURLにアクセス
2. チャットインタビューに回答
3. 画像生成をテスト

## 🔧 トラブルシューティング

### ビルドエラーの場合
- Cloud Build → 履歴 でログを確認
- Dockerfileのパスが正しいか確認

### デプロイエラーの場合
- Cloud Run → ログ でエラー内容を確認
- メモリ不足の場合は割り当てを増やす

### CORSエラーの場合
- バックエンドの`main.py`でCORS設定を確認
- フロントエンドの環境変数が正しいか確認

### 画像生成が失敗する場合
- `NANOBANANA_API_KEY`が正しく設定されているか確認
- Cloud Run → ログ でAPIエラーを確認

## 💰 料金の目安

- **Cloud Run**: 
  - 無料枠: 200万リクエスト/月
  - CPU: 180,000 vCPU秒/月
  - メモリ: 360,000 GiB秒/月
  
- **Cloud Build**:
  - 無料枠: 120分/日
  
- **Container Registry**:
  - ストレージ料金のみ（約$0.026/GB/月）

## 🔒 セキュリティ推奨事項

1. **Secret Manager の使用**（上級者向け）
   - APIキーをSecret Managerに保存
   - Cloud RunからSecret Managerを参照

2. **Identity Aware Proxy (IAP)**（企業向け）
   - 認証が必要な場合はIAPを設定

3. **カスタムドメイン**
   - Cloud Run → カスタムドメイン から独自ドメインを設定可能

## 📝 メモ

- デプロイ完了まで約10-15分
- 初回アクセス時は起動に数秒かかる場合があります
- 自動スケーリングにより、アクセスがない時はインスタンス0になります