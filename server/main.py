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
from PIL import Image
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Vertex AI設定
PROJECT_ID = "makeillust"
LOCATION = "asia-northeast1"  # または "us-central1"

# Vertex AIを初期化
try:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    # ImageGenerationModelをロード
    image_model = ImageGenerationModel.from_pretrained("imagegeneration@006")
    logger.info(f"Vertex AI initialized with project={PROJECT_ID}, location={LOCATION}")
except Exception as e:
    logger.error(f"Failed to initialize Vertex AI: {e}")
    image_model = None

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
        "vertex_ai_configured": bool(image_model),
        "project": PROJECT_ID,
        "location": LOCATION,
        "environment": os.getenv("K_SERVICE", "local"),
        "api_type": "Vertex AI ImageGeneration"
    }

def generate_image_with_vertex(prompt: str) -> bytes:
    """Vertex AI ImageGenerationModelで画像を生成"""
    if not image_model:
        raise HTTPException(status_code=500, detail="Vertex AI not initialized")
    
    try:
        # Vertex AIで画像を生成
        response = image_model.generate_images(
            prompt=prompt,
            number_of_images=1,
            language="en",
            add_watermark=False,
            aspect_ratio="9:16",  # 立ち絵用の縦長比率
            safety_filter_level="block_some",
            person_generation="allow_adult"
        )
        
        # 生成された画像を取得
        if response.images:
            # 画像をバイト列に変換
            image = response.images[0]
            buffered = io.BytesIO()
            image._pil_image.save(buffered, format="PNG")
            return buffered.getvalue()
        else:
            raise Exception("No image generated")
            
    except Exception as e:
        logger.error(f"Vertex AI image generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

def create_image_prompt(character: Character, expression: str) -> str:
    """キャラクター情報から画像生成用プロンプトを作成"""
    
    # 表情の説明を日本語から英語に変換
    expression_map = {
        "ニュートラル": "neutral calm expression",
        "微笑み": "gentle smile, slightly raised mouth corners",
        "驚き": "surprised expression with wide eyes and slightly open mouth",
        "困り顔": "troubled expression with worried eyebrows",
        "むすっ": "pouting expression with furrowed brows"
    }
    
    expression_desc = expression_map.get(expression, "neutral expression")
    
    # 髪飾りがある場合のテキスト
    hair_accessories = f", with {', '.join(character.hair.accessories)}" if character.hair.accessories else ""
    
    # 顔の特徴がある場合のテキスト
    face_marks = f", with {', '.join(character.face.marks)}" if character.face.marks else ""
    
    # アクセサリーがある場合のテキスト
    outfit_accessories = f", wearing {', '.join(character.outfit.accessories)}" if character.outfit.accessories else ""
    
    prompt = f"""Create a high-quality anime-style standing character illustration with the following specifications:

Character Details:
- Age appearance: {character.basic.age_appearance}
- Height: {character.basic.height_cm}cm, {character.basic.build} build
- Hair: {character.hair.color} colored {character.hair.length} hair, {character.hair.style} style, {character.hair.bangs} bangs{hair_accessories}
- Eyes: {character.face.eyes_color} colored {character.face.eyes_shape} eyes with {character.face.eyelashes} eyelashes
- Eyebrows: {character.face.eyebrows}
- Mouth: {character.face.mouth}
- Facial features: {face_marks if face_marks else 'none'}
- Expression: {expression_desc}
- Outfit: {character.outfit.style}, wearing {character.outfit.top} on top, {character.outfit.bottom} on bottom, {character.outfit.shoes} shoes{outfit_accessories}
- Personality: {', '.join(character.persona.keywords)}
- Role: {character.persona.role}

Visual Requirements:
- Full body standing pose, showing from head to toe
- Front facing camera angle, no tilt or perspective
- Arms naturally at sides, relaxed posture
- Pure white background (#FFFFFF)
- Clean anime/manga art style with soft colors
- No shadows, no floor reflection, no background objects
- High quality, detailed illustration
- Consistent character design

Style: Japanese anime/manga illustration, soft pastel colors, clean lines, professional quality"""
    
    return prompt

@app.post("/api/generate")
async def generate_images(request: GenerateRequest):
    """キャラクター画像を生成するメインエンドポイント"""
    try:
        # Vertex AIの初期化確認
        if not image_model:
            logger.error("Vertex AI ImageGenerationModel is not initialized")
            raise HTTPException(
                status_code=500,
                detail="Vertex AI is not configured properly."
            )
        
        logger.info(f"Generating images for character: {request.character.character_id}")
        
        # 各表情用の画像を生成
        expressions = ["ニュートラル", "微笑み", "驚き", "困り顔", "むすっ"]
        images = []
        prompts = []
        
        for expression in expressions:
            logger.info(f"Generating image for expression: {expression}")
            
            # プロンプトを作成
            prompt = create_image_prompt(request.character, expression)
            prompts.append(prompt)
            logger.info(f"Created prompt for {expression}: {prompt[:100]}...")
            
            # Vertex AIで画像を生成
            try:
                image_bytes = generate_image_with_vertex(prompt)
                images.append(image_bytes)
                logger.info(f"Successfully generated image for {expression}")
            except Exception as e:
                logger.error(f"Failed to generate image for {expression}: {str(e)}")
                # エラーが発生した場合、エラーを送出
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to generate image for {expression}: {str(e)}"
                )
        
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