import os
import io
import base64
import zipfile
import logging
import json
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import requests
from rembg import remove
from PIL import Image, ImageDraw, ImageFont
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Cloud API設定
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"

app = FastAPI(title="Standing-Set-5 API with Google Cloud")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models (同じものを使用)
class BasicInfo(BaseModel):
    age_appearance: str = Field(..., description="年齢感")
    height_cm: int = Field(..., ge=120, le=200, description="身長(cm)")
    build: str = Field(..., description="体格")

class HairInfo(BaseModel):
    color: str = Field(..., description="髪色")
    length: str = Field(..., description="髪の長さ")
    bangs: str = Field(..., description="前髪")
    style: str = Field(..., description="髪型")
    accessories: List[str] = Field(default_factory=list, description="髪飾り")

class FaceInfo(BaseModel):
    eyes_color: str = Field(..., description="目の色")
    eyes_shape: str = Field(..., description="目の形")
    eyelashes: str = Field(..., description="まつ毛")
    eyebrows: str = Field(..., description="眉")
    mouth: str = Field(..., description="口")
    marks: List[str] = Field(default_factory=list, description="特徴（ほくろ等）")

class OutfitInfo(BaseModel):
    style: str = Field(..., description="服装スタイル")
    top: str = Field(..., description="上衣")
    bottom: str = Field(..., description="下衣")
    accessories: List[str] = Field(default_factory=list, description="小物")
    shoes: str = Field(..., description="靴")

class PersonaInfo(BaseModel):
    keywords: List[str] = Field(..., description="性格キーワード")
    role: str = Field(..., description="役割")

class FramingInfo(BaseModel):
    shot: str = Field(default="全身", description="ショットタイプ")
    camera: str = Field(default="正面、俯瞰なし、中心に全身が収まる、左右の余白を確保", description="カメラアングル")
    pose: str = Field(default="直立、両腕は体側、自然体、足元まで映る", description="ポーズ")

class ConstraintsInfo(BaseModel):
    background: str = Field(default="白", description="背景")
    forbid: List[str] = Field(
        default=["背景小物", "武器", "他キャラ", "文字", "透かし", "テクスチャ", "床影", "強コントラスト"],
        description="禁止事項"
    )

class Character(BaseModel):
    character_id: str = Field(..., description="キャラクターID")
    seed: int = Field(default=123456789, description="シード値")
    basic: BasicInfo
    hair: HairInfo
    face: FaceInfo
    outfit: OutfitInfo
    persona: PersonaInfo
    framing: FramingInfo = Field(default_factory=FramingInfo)
    constraints: ConstraintsInfo = Field(default_factory=ConstraintsInfo)

class GenerateRequest(BaseModel):
    character: Character
    return_type: str = Field(default="base64_list", description="返却形式: 'zip' or 'base64_list'")

@app.get("/api/health")
def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy", 
        "api_key_configured": bool(GOOGLE_API_KEY),
        "api_key_length": len(GOOGLE_API_KEY) if GOOGLE_API_KEY else 0,
        "environment": os.getenv("K_SERVICE", "local"),
        "api_type": "Google Cloud Gemini"
    }

def generate_with_gemini(prompt: str) -> str:
    """Geminiを使ってテキスト生成（プロンプトの詳細化など）"""
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Google API key not configured")
    
    headers = {
        "Content-Type": "application/json",
    }
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(
            f"{GEMINI_API_URL}?key={GOOGLE_API_KEY}",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code >= 400:
            logger.error(f"Gemini API error: {response.status_code} - {response.text}")
            return prompt  # フォールバック
        
        data = response.json()
        if "candidates" in data and len(data["candidates"]) > 0:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        
        return prompt
        
    except Exception as e:
        logger.error(f"Gemini API error: {str(e)}")
        return prompt

def generate_placeholder_images(character: Character) -> List[bytes]:
    """
    Google Cloud APIで画像生成する代わりに、一時的にプレースホルダー画像を生成
    実際のプロダクションでは、Vertex AI の Imagen APIを使用
    """
    expressions = [
        "ニュートラル",
        "微笑み",
        "驚き", 
        "困り顔",
        "むすっ"
    ]
    
    images = []
    
    for i, expression in enumerate(expressions):
        # 512x768のプレースホルダー画像を作成
        img = Image.new('RGBA', (512, 768), color=(255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        # 背景
        draw.rectangle([0, 0, 512, 768], fill=(250, 250, 250, 255))
        
        # キャラクター情報を表示
        y_offset = 50
        
        # タイトル
        draw.text((256, y_offset), f"表情: {expression}", fill=(0, 0, 0), anchor="mt")
        y_offset += 50
        
        # キャラクター情報
        info_lines = [
            f"年齢: {character.basic.age_appearance}",
            f"身長: {character.basic.height_cm}cm",
            f"髪色: {character.hair.color}",
            f"髪型: {character.hair.style}",
            f"目の色: {character.face.eyes_color}",
            f"服装: {character.outfit.style}",
            f"性格: {', '.join(character.persona.keywords)}",
            f"役割: {character.persona.role}"
        ]
        
        for line in info_lines:
            draw.text((256, y_offset), line, fill=(50, 50, 50), anchor="mt")
            y_offset += 40
        
        # シンプルな顔を描画（表情別）
        face_y = 400
        # 顔の輪郭
        draw.ellipse([206, face_y, 306, face_y+100], outline=(100, 100, 100), width=2)
        
        # 目
        if expression == "驚き":
            draw.ellipse([225, face_y+30, 245, face_y+50], outline=(0, 0, 0), width=2)
            draw.ellipse([267, face_y+30, 287, face_y+50], outline=(0, 0, 0), width=2)
        elif expression == "微笑み":
            draw.arc([225, face_y+35, 245, face_y+45], start=0, end=180, fill=(0, 0, 0), width=2)
            draw.arc([267, face_y+35, 287, face_y+45], start=0, end=180, fill=(0, 0, 0), width=2)
        else:
            draw.ellipse([230, face_y+35, 240, face_y+45], fill=(0, 0, 0))
            draw.ellipse([272, face_y+35, 282, face_y+45], fill=(0, 0, 0))
        
        # 口
        if expression == "微笑み":
            draw.arc([236, face_y+60, 276, face_y+80], start=0, end=180, fill=(0, 0, 0), width=2)
        elif expression == "驚き":
            draw.ellipse([246, face_y+65, 266, face_y+80], outline=(0, 0, 0), width=2)
        elif expression == "困り顔":
            draw.arc([236, face_y+70, 276, face_y+80], start=180, end=0, fill=(0, 0, 0), width=2)
        elif expression == "むすっ":
            draw.line([246, face_y+70, 266, face_y+70], fill=(0, 0, 0), width=2)
        else:
            draw.line([246, face_y+70, 266, face_y+70], fill=(0, 0, 0), width=1)
        
        # 画像をバイト列に変換
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        images.append(buf.getvalue())
    
    return images

def create_detailed_prompt_with_gemini(character: Character, expression: str) -> str:
    """Geminiを使って詳細なプロンプトを生成"""
    base_prompt = f"""
    次のキャラクターの立ち絵画像の詳細なプロンプトを生成してください：
    
    キャラクター情報:
    - 年齢: {character.basic.age_appearance}
    - 身長: {character.basic.height_cm}cm、体型: {character.basic.build}
    - 髪: {character.hair.color}の{character.hair.length}、{character.hair.style}
    - 目: {character.face.eyes_color}の{character.face.eyes_shape}
    - 服装: {character.outfit.style}
    - 性格: {', '.join(character.persona.keywords)}
    - 役割: {character.persona.role}
    - 表情: {expression}
    
    以下の条件で、Stable DiffusionやMidjourneyで使えるような英語のプロンプトを生成してください：
    - アニメ/マンガスタイル
    - 全身立ち絵
    - 白背景
    - 正面向き
    - 高品質
    
    プロンプトのみを返してください。
    """
    
    return generate_with_gemini(base_prompt)

@app.post("/api/generate")
async def generate_images(request: GenerateRequest):
    """キャラクター画像を生成するメインエンドポイント"""
    try:
        # APIキーの確認
        if not GOOGLE_API_KEY:
            logger.error("GOOGLE_API_KEY is not set")
            raise HTTPException(
                status_code=500,
                detail="API key is not configured. Please set GOOGLE_API_KEY environment variable."
            )
        
        logger.info(f"Generating images for character: {request.character.character_id}")
        
        # 各表情用のプロンプトを生成（Geminiを使用）
        expressions = ["ニュートラル", "微笑み", "驚き", "困り顔", "むすっ"]
        prompts = []
        
        for expression in expressions:
            prompt = create_detailed_prompt_with_gemini(request.character, expression)
            prompts.append(prompt)
            logger.info(f"Generated prompt for {expression}: {prompt[:100]}...")
        
        # 画像生成
        # 注: 実際のプロダクションでは、ここでVertex AI Imagen APIを呼び出します
        # 現在はプレースホルダー画像を生成
        images = generate_placeholder_images(request.character)
        
        logger.info(f"Generated {len(images)} images")
        
        # 背景除去（オプション）
        processed_images = []
        for i, img_bytes in enumerate(images):
            try:
                # rembgで背景除去
                processed = remove(Image.open(io.BytesIO(img_bytes)))
                buf = io.BytesIO()
                processed.save(buf, format="PNG")
                processed_images.append(buf.getvalue())
            except Exception as e:
                logger.warning(f"Background removal failed for image {i}: {str(e)}")
                processed_images.append(img_bytes)
        
        # 返却形式に応じて処理
        if request.return_type == "base64_list":
            base64_images = [
                base64.b64encode(img).decode("utf-8") 
                for img in processed_images
            ]
            return {
                "images": base64_images,
                "message": f"Successfully generated {len(base64_images)} images",
                "prompts": prompts  # デバッグ用にプロンプトも返す
            }
        
        # ZIP形式で返却
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for i, img_bytes in enumerate(processed_images, 1):
                filename = f"{request.character.character_id}_expr{i:02d}.png"
                zip_file.writestr(filename, img_bytes)
        
        zip_buffer.seek(0)
        
        headers = {
            "Content-Disposition": f"attachment; filename=standing_set_{request.character.character_id}.zip"
        }
        
        return Response(
            content=zip_buffer.read(),
            media_type="application/zip",
            headers=headers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Generation failed: {str(e)}"
        )

@app.get("/")
def root():
    """ルートエンドポイント"""
    return {
        "name": "Standing-Set-5 API",
        "version": "2.0.0",
        "api_provider": "Google Cloud (Gemini)",
        "endpoints": {
            "health": "/api/health",
            "generate": "/api/generate",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)