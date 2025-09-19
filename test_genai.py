#!/usr/bin/env python3
import os
import sys

# APIキーをテスト用に設定（実際のキーを設定してください）
# os.environ["GOOGLE_API_KEY"] = "YOUR_API_KEY_HERE"

try:
    from google import genai
    print("✅ google-genai package imported successfully")
    
    # APIキーが設定されているか確認
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        print(f"✅ API key configured (length: {len(api_key)})")
        
        # クライアントを初期化
        client = genai.Client(api_key=api_key)
        print("✅ Gemini client initialized")
        
        # 簡単なテキスト生成テスト（画像生成ではない）
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents="Say hello in one word"
            )
            print(f"✅ API response test: {response.text}")
        except Exception as e:
            print(f"❌ API call failed: {e}")
            print(f"   Error type: {type(e).__name__}")
    else:
        print("❌ GOOGLE_API_KEY not set")
        
except ImportError as e:
    print(f"❌ Failed to import google-genai: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    print(f"   Error type: {type(e).__name__}")