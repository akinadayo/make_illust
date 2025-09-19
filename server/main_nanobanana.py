import os
import io
import base64
import zipfile
import logging
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import requests
from rembg import remove
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NANO_URL = "https://api.nanobanana.ai/v1/images/generations"
API_KEY = os.getenv("NANOBANANA_API_KEY")

app = FastAPI(title="Standing-Set-5 API")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
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
    return_type: str = Field(default="zip", description="返却形式: 'zip' or 'base64_list'")

class GenerateResponse(BaseModel):
    images: Optional[List[str]] = None
    message: Optional[str] = None

@app.get("/api/health")
def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy", 
        "api_key_configured": bool(API_KEY),
        "api_key_length": len(API_KEY) if API_KEY else 0,
        "environment": os.getenv("K_SERVICE", "local")
    }

def join_list(items: List[str]) -> str:
    """リストを文字列に結合"""
    return ", ".join(items) if items else ""

def render_prompt(char: Character) -> str:
    """キャラクター情報からプロンプトを生成"""
    d = char.dict()
    
    prompt = f"""【目的】
同一キャラクターのラノベ風立ち絵を5枚同時に生成する。
5枚は人物・髪・衣装・体格・画角・線のタッチを完全一致させ、顔の表情だけを各枚ごとに変更する。
背景は完全に白（#FFFFFF）。質感テクスチャや落ち影は一切入れない。全身が頭からつま先までフレーム内に完全に収まること。

【色調（数値を使わない指定）】
overall color grading: pale tones, light grayish tones, soft muted pastel tones.
airy and slightly hazy atmosphere, emotional pastel look.
no vivid or highly saturated colors, no harsh contrast.
low-contrast tonal range, avoid crushed blacks and clipped whites.

【線（輪郭）】
outline color: soft, desaturated cool gray; not pure black.
outer contour lines: slightly bolder to hold silhouette.
inner facial/detail lines: finer and lighter gray.
consistent, clean, thin lines; no sketchy strokes or messy hatching.

【ライティング】
soft, diffused frontal key light.
gentle ambient light with a cool tint.
shadows should be light grayish, never pure black.
very thin cool rim light for subtle depth.
overall gentle, low-contrast illumination.

【キャラクター固定仕様（全画像共通・厳守）】
年齢感: {d['basic']['age_appearance']}
身長: {d['basic']['height_cm']}cm前後 / 体格: {d['basic']['build']}
髪: {d['hair']['color']}, {d['hair']['length']}, 前髪: {d['hair']['bangs']}, スタイル: {d['hair']['style']}, アクセ: {join_list(d['hair'].get('accessories', []))}
顔: 目色 {d['face']['eyes_color']}, 目形 {d['face']['eyes_shape']}, まつ毛 {d['face']['eyelashes']}, 眉 {d['face']['eyebrows']}, 口 {d['face']['mouth']}, 特徴 {join_list(d['face'].get('marks', []))}
服装: {d['outfit']['style']} / 上 {d['outfit']['top']} / 下 {d['outfit']['bottom']} / 小物 {join_list(d['outfit'].get('accessories', []))} / 靴 {d['outfit']['shoes']}
性格キーワード: {join_list(d['persona'].get('keywords', []))} / 役割: {d['persona']['role']}

【構図・フレーミング（全画像共通・厳守）】
ショット: 全身。頭から足先まで切れずにフレーム内に収める。左右にわずかな余白を取り、中央に配置。
カメラ: 正面、俯瞰なし、50mm相当の自然なパース。レンズ歪みなし。被写界深度は深く、全身にフォーカス。
ポーズ: 直立、肩の力みなし、両腕は体側、指先は自然。足元まで見える。足の向きは正面〜やや内振り程度。
背景: 完全な白 (#FFFFFF)。no texture, no vignette, no gradient, no floor shadow.

【禁止（全画像）】
背景小物、武器、他キャラ、文字、透かし（watermark）、粒子ノイズ、紙テクスチャ、床影・床反射、過度な光沢、強コントラスト、切れフレーミング。

【出力ルール】
- 合計5枚。全画像で同一人物としての一貫性を最優先。
- 差分は「顔の表情のみ」。髪・衣装・体格・ポーズ・画角・線の太さは完全固定。
- 画像順序は #1→#5 の順に返す。

【各画像の表情差分（顔のみ変更）】
#1: ニュートラル — 穏やかな基準表情
    口: 自然 / 眉: 標準 / 目: 標準

#2: 微笑み — 口角をわずかに上げた優しい笑顔
    口: 軽いスマイル / 眉: やや下げ / 目: やや細め

#3: 驚き — 目を丸くして小さく口を開く
    口: 小さく開く / 眉: 上がる / 目: 大きく

#4: 困り顔 — 申し訳なさそうに眉が寄る
    口: への字（小） / 眉: 内側に寄る / 目: やや細め

#5: むすっ — 拗ねたように正面を見据える
    口: 真一文字 / 眉: 下がる / 目: 標準"""
    
    return prompt.strip()

def nano_generate(prompt: str, seed: int, width: int = 1024, height: int = 1536) -> List[bytes]:
    """NanoBanana APIを呼び出して画像を生成"""
    if not API_KEY:
        raise HTTPException(status_code=500, detail="NANOBANANA_API_KEY is not configured")
    
    payload = {
        "prompt": prompt,
        "n": 5,
        "seed": seed,
        "width": width,
        "height": height,
        "model": "nano",  # or appropriate model name
    }
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        logger.info("Calling NanoBanana API...")
        response = requests.post(NANO_URL, headers=headers, json=payload, timeout=300)
        
        if response.status_code >= 400:
            logger.error(f"NanoBanana API error: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"NanoBanana API error: {response.text}"
            )
        
        data = response.json()
        images = []
        
        # Extract images from response
        if "data" in data:
            for item in data["data"]:
                if "b64_json" in item:
                    img_bytes = base64.b64decode(item["b64_json"])
                    images.append(img_bytes)
        elif "images" in data:
            for item in data["images"]:
                if "b64_json" in item:
                    img_bytes = base64.b64decode(item["b64_json"])
                    images.append(img_bytes)
                elif "url" in item:
                    # If URL is returned, fetch the image
                    img_response = requests.get(item["url"], timeout=30)
                    images.append(img_response.content)
        
        if len(images) != 5:
            logger.warning(f"Expected 5 images but got {len(images)}")
            if len(images) == 0:
                raise HTTPException(
                    status_code=500,
                    detail="No images returned from NanoBanana API"
                )
        
        return images
        
    except requests.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to NanoBanana API: {str(e)}"
        )

def remove_background(image_bytes: bytes) -> bytes:
    """rembgを使って背景を除去"""
    try:
        # Open image from bytes
        img = Image.open(io.BytesIO(image_bytes))
        
        # Apply background removal
        output = remove(img)
        
        # Save to bytes
        buf = io.BytesIO()
        output.save(buf, format="PNG")
        buf.seek(0)
        
        return buf.getvalue()
    except Exception as e:
        logger.error(f"Background removal failed: {str(e)}")
        # Return original image if removal fails
        return image_bytes

@app.post("/api/generate")
async def generate_images(request: GenerateRequest):
    """キャラクター画像を生成するメインエンドポイント"""
    try:
        # APIキーの確認
        if not API_KEY:
            logger.error("NANOBANANA_API_KEY is not set")
            raise HTTPException(
                status_code=500,
                detail="API key is not configured. Please set NANOBANANA_API_KEY environment variable."
            )
        
        # Generate prompt from character data
        prompt = render_prompt(request.character)
        logger.info(f"Generated prompt for character: {request.character.character_id}")
        logger.info(f"API Key configured: {'Yes' if API_KEY else 'No'}")
        
        # Call NanoBanana API
        raw_images = nano_generate(
            prompt=prompt,
            seed=request.character.seed
        )
        logger.info(f"Received {len(raw_images)} images from NanoBanana")
        
        # Remove background from each image
        processed_images = []
        for i, img_bytes in enumerate(raw_images):
            logger.info(f"Processing image {i+1}/5...")
            processed = remove_background(img_bytes)
            processed_images.append(processed)
        
        # Return based on requested format
        if request.return_type == "base64_list":
            # Return as base64 encoded list
            base64_images = [
                base64.b64encode(img).decode("utf-8") 
                for img in processed_images
            ]
            return {
                "images": base64_images,
                "message": f"Successfully generated 5 images for {request.character.character_id}"
            }
        
        # Default: Return as ZIP file
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
        "version": "1.0.0",
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