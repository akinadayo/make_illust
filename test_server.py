#!/usr/bin/env python3
import os
import sys

# サーバーディレクトリをパスに追加
sys.path.insert(0, '/Users/dcenter/Desktop/立ち絵生成')

# テスト用のAPIキー（実際には設定されていない）
os.environ["GOOGLE_API_KEY"] = "test-key-for-import"

try:
    # サーバーのインポートをテスト
    print("Attempting to import server modules...")
    
    from google import genai
    print("✅ google-genai imported")
    
    from google.genai import types
    print("✅ google.genai.types imported")
    
    # FastAPIとその他のインポートをテスト
    from fastapi import FastAPI, HTTPException, Response
    print("✅ FastAPI imported")
    
    from pydantic import BaseModel, Field
    print("✅ Pydantic imported")
    
    from PIL import Image
    print("✅ PIL imported")
    
    from rembg import remove
    print("✅ rembg imported")
    
    print("\n✅ All imports successful!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"   Module: {e.name if hasattr(e, 'name') else 'unknown'}")
    print(f"   Path: {e.path if hasattr(e, 'path') else 'unknown'}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    print(f"   Error type: {type(e).__name__}")