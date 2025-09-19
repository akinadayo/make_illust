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
from google.auth import default
from google.auth.transport.requests import Request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Vertex AI設定
PROJECT_ID = "makeillust"
LOCATION = "us-central1"  # Imagen APIは us-central1 のみサポート
MODEL_ID = "imagen-4.0-generate-001"
ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL_ID}:predict"

# 認証情報を取得
credentials = None
try:
    credentials, project = default()
    logger.info(f"Using default credentials for project: {project}")
except Exception as e:
    logger.error(f"Failed to get default credentials: {e}")

app = FastAPI(title="Standing-Set-5 API with Google Cloud")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simplified Pydantic Models
class SimpleCharacter(BaseModel):
    character_id: str = Field(default="char_001", description="キャラクターID")
    seed: int = Field(default=123456789, description="シード値")
    age: str = Field(..., description="年齢（例：16歳、20代前半）")
    body_type: str = Field(..., description="体型（例：細身、標準、がっちり）")
    eyes: str = Field(..., description="目の特徴（例：大きい茶色の目、鋭い青い目）")
    hair: str = Field(..., description="髪型と色（例：黒のロングストレート、金髪のショートボブ）")
    outfit: str = Field(..., description="服装（例：制服、カジュアルな私服、スーツ）")
    accessories: Optional[str] = Field(default="", description="アクセサリー（例：眼鏡、リボン、ネックレス）")
    other_features: Optional[str] = Field(default="", description="その他の特徴（例：ほくろ、傷跡、タトゥー）")

# 互換性のため、古い形式も残しておく
class Character(BaseModel):
    character_id: str = Field(..., description="キャラクターID")
    seed: int = Field(default=123456789, description="シード値")
    basic: Dict[str, Any] = Field(default_factory=dict)
    hair: Dict[str, Any] = Field(default_factory=dict)
    face: Dict[str, Any] = Field(default_factory=dict)
    outfit: Dict[str, Any] = Field(default_factory=dict)
    persona: Dict[str, Any] = Field(default_factory=dict)
    framing: Dict[str, Any] = Field(default_factory=dict)
    constraints: Dict[str, Any] = Field(default_factory=dict)

class GenerateRequest(BaseModel):
    character: Character
    return_type: str = Field(default="base64_list", description="返却形式: 'zip' or 'base64_list'")

class SimpleGenerateRequest(BaseModel):
    character: SimpleCharacter
    return_type: str = Field(default="base64_list", description="返却形式: 'zip' or 'base64_list'")

@app.get("/api/health")
def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy", 
        "credentials_configured": bool(credentials),
        "project": PROJECT_ID,
        "location": LOCATION,
        "model": MODEL_ID,
        "environment": os.getenv("K_SERVICE", "local"),
        "api_type": "Vertex AI Imagen 4.0"
    }

def generate_images_with_vertex_simple(character: SimpleCharacter) -> List[bytes]:
    """簡略化されたキャラクター情報でVertex AI Imagen 4.0で4枚の表情違い画像を一度に生成"""
    if not credentials:
        raise HTTPException(status_code=500, detail="Credentials not configured")
    
    try:
        # アクセストークンを取得
        if hasattr(credentials, 'refresh'):
            credentials.refresh(Request())
        
        access_token = credentials.token
        
        # 4つの表情を仕様書通りに定義
        expressions = [
            """
【各画像の表情差分（顔のみ変更）】
#1: ニュートラル — 穏やかな基準表情
    口: 自然 / 眉: 標準 / 目: 標準""",
            """
【各画像の表情差分（顔のみ変更）】
#2: 照れながら微笑み — 口角をわずかに上げた優しい笑顔
    口: 軽いスマイル / 眉: やや下げ / 目: やや細め""",
            """
【各画像の表情差分（顔のみ変更）】
#3: 困り顔 — 申し訳なさそうに眉が寄る
    口: への字（小） / 眉: 内側に寄る / 目: やや細め""",
            """
【各画像の表情差分（顔のみ変更）】
#4: むすっ — 拗ねたように正面を見据える
    口: 真一文字 / 眉: 下がる / 目: 標準"""
        ]
        
        # 基本プロンプトを作成（簡略化版）
        base_prompt = create_simple_prompt_without_expression(character)
        
        # 4つのプロンプトを作成（各表情を追加）
        prompts = [f"{base_prompt}\n{expr}" for expr in expressions]
        
        # デバッグ用：生成されるプロンプトをログに出力
        for i, prompt in enumerate(prompts):
            logger.info(f"Simple Prompt {i+1} ({['ニュートラル', '照れながら微笑み', '困り顔', 'むすっ'][i]}): {prompt[:200]}...")
        
        # 各表情ごとに個別のAPIリクエストを送信（Imagen 4.0は1インスタンスのみサポート）
        images = []
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        for i, prompt in enumerate(prompts):
            expression_name = ['ニュートラル', '照れながら微笑み', '困り顔', 'むすっ'][i]
            logger.info(f"Generating expression {i+1}/4: {expression_name}")
            
            # 各表情用のリクエストボディ
            request_body = {
                "instances": [{"prompt": prompt}],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": "9:16",
                    "negativePrompt": "low quality, blurry, watermark, text, signature, multiple people, inconsistent character, white background",
                    "seed": character.seed + i,  # 各表情で少しずつseedを変える
                    "addWatermark": False
                }
            }
            
            response = requests.post(
                ENDPOINT,
                headers=headers,
                json=request_body,
                timeout=120
            )
            
            if response.status_code != 200:
                logger.error(f"Vertex AI API error for expression {expression_name}: {response.status_code} - {response.text}")
                raise Exception(f"API error for {expression_name}: {response.status_code} - {response.text}")
            
            # レスポンスから画像を取得
            result = response.json()
            
            if "predictions" in result and len(result["predictions"]) > 0:
                prediction = result["predictions"][0]
                if "bytesBase64Encoded" in prediction:
                    image_data = base64.b64decode(prediction["bytesBase64Encoded"])
                    images.append(image_data)
                elif "image" in prediction:
                    image_data = base64.b64decode(prediction["image"])
                    images.append(image_data)
                else:
                    logger.error(f"No image data in prediction for {expression_name}")
                    raise Exception(f"No image data for {expression_name}")
            else:
                logger.error(f"No predictions in response for {expression_name}: {result}")
                raise Exception(f"No predictions for {expression_name}")
        
        if len(images) != 4:
            logger.warning(f"Expected 4 images, got {len(images)}")
            
        return images
            
    except Exception as e:
        logger.error(f"Vertex AI image generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

def generate_images_with_vertex(character: Character) -> List[bytes]:
    """Vertex AI Imagen 4.0で4枚の表情違い画像を一度に生成"""
    if not credentials:
        raise HTTPException(status_code=500, detail="Credentials not configured")
    
    try:
        # アクセストークンを取得
        if hasattr(credentials, 'refresh'):
            credentials.refresh(Request())
        
        access_token = credentials.token
        
        # 4つの表情を仕様書通りに定義
        expressions = [
            """
【各画像の表情差分（顔のみ変更）】
#1: ニュートラル — 穏やかな基準表情
    口: 自然 / 眉: 標準 / 目: 標準""",
            """
【各画像の表情差分（顔のみ変更）】
#2: 照れながら微笑み — 口角をわずかに上げた優しい笑顔
    口: 軽いスマイル / 眉: やや下げ / 目: やや細め""",
            """
【各画像の表情差分（顔のみ変更）】
#3: 困り顔 — 申し訳なさそうに眉が寄る
    口: への字（小） / 眉: 内側に寄る / 目: やや細め""",
            """
【各画像の表情差分（顔のみ変更）】
#4: むすっ — 拗ねたように正面を見据える
    口: 真一文字 / 眉: 下がる / 目: 標準"""
        ]
        
        # 基本プロンプトを作成（表情以外の共通部分）
        base_prompt = create_base_prompt_without_expression(character)
        
        # 4つのプロンプトを作成（各表情を追加）
        prompts = [f"{base_prompt}\n{expr}" for expr in expressions]
        
        # デバッグ用：生成されるプロンプトをログに出力
        for i, prompt in enumerate(prompts):
            logger.info(f"Prompt {i+1} ({['ニュートラル', '照れながら微笑み', '困り顔', 'むすっ'][i]}): {prompt}")
        
        # 各表情ごとに個別のAPIリクエストを送信（Imagen 4.0は1インスタンスのみサポート）
        images = []
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        for i, prompt in enumerate(prompts):
            expression_name = ['ニュートラル', '照れながら微笑み', '困り顔', 'むすっ'][i]
            logger.info(f"Generating expression {i+1}/4: {expression_name}")
            
            # 各表情用のリクエストボディ
            request_body = {
                "instances": [{"prompt": prompt}],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": "9:16",
                    "negativePrompt": "low quality, blurry, watermark, text, signature, multiple people, inconsistent character, white background",
                    "seed": character.seed + i,  # 各表情で少しずつseedを変える
                    "addWatermark": False
                }
            }
            
            response = requests.post(
                ENDPOINT,
                headers=headers,
                json=request_body,
                timeout=120
            )
            
            if response.status_code != 200:
                logger.error(f"Vertex AI API error for expression {expression_name}: {response.status_code} - {response.text}")
                raise Exception(f"API error for {expression_name}: {response.status_code} - {response.text}")
            
            # レスポンスから画像を取得
            result = response.json()
            
            if "predictions" in result and len(result["predictions"]) > 0:
                prediction = result["predictions"][0]
                if "bytesBase64Encoded" in prediction:
                    image_data = base64.b64decode(prediction["bytesBase64Encoded"])
                    images.append(image_data)
                elif "image" in prediction:
                    image_data = base64.b64decode(prediction["image"])
                    images.append(image_data)
                else:
                    logger.error(f"No image data in prediction for {expression_name}")
                    raise Exception(f"No image data for {expression_name}")
            else:
                logger.error(f"No predictions in response for {expression_name}: {result}")
                raise Exception(f"No predictions for {expression_name}")
        
        if len(images) != 4:
            logger.warning(f"Expected 4 images, got {len(images)}")
        
        return images
            
    except Exception as e:
        logger.error(f"Vertex AI image generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

def remove_green_background(image_bytes: bytes) -> bytes:
    """グリーンバックを透明にする"""
    try:
        # 画像を開く
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGBA")
        
        # 画像データを取得
        data = img.getdata()
        
        # 新しい画像データ
        new_data = []
        
        # グリーンの閾値（調整可能）
        green_threshold = 100  # 緑の強さ
        red_threshold = 100    # 赤の上限
        blue_threshold = 100   # 青の上限
        
        for item in data:
            # RGB値を取得
            r, g, b, a = item
            
            # グリーンスクリーンの判定（緑が強く、赤と青が弱い）
            if g > green_threshold and r < red_threshold and b < blue_threshold:
                # 透明にする
                new_data.append((r, g, b, 0))
            else:
                # そのまま保持
                new_data.append(item)
        
        # 新しい画像を作成
        img.putdata(new_data)
        
        # バイト列に変換
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Green background removal error: {str(e)}")
        raise

def create_simple_prompt_without_expression(character: SimpleCharacter) -> str:
    """簡略化されたキャラクター情報から仕様書フォーマットのプロンプトを作成"""
    
    prompt = f"""【目的】
同一キャラクターのラノベ風立ち絵を4枚同時に生成する。
4枚は人物・髪・衣装・体格・画角・線のタッチを完全一致させ、顔の表情だけを各枚ごとに変更する。
背景は完全にビビッドなグリーン#00FF00。質感テクスチャや落ち影は一切入れない。全身が頭からつま先までフレーム内に完全に収まること。

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
年齢: {character.age}
体型: {character.body_type}
目: {character.eyes}
髪: {character.hair}
服装: {character.outfit}
アクセサリー: {getattr(character, 'accessories', '') or "なし"}
その他の特徴: {getattr(character, 'other_features', '') or "なし"}

【構図・フレーミング（全画像共通・厳守）】
ショット: 全身。頭から足先まで切れずにフレーム内に収める。左右にわずかな余白を取り、中央に配置。
カメラ: 正面、俯瞰なし、50mm相当の自然なパース。レンズ歪みなし。被写界深度は深く、全身にフォーカス。
ポーズ: 直立、肩の力みなし、両腕は体側、指先は自然。足元まで見える。足の向きは正面〜やや内振り程度。
背景: 完全なグリーン (#00FF00)。no texture, no vignette, no gradient, no floor shadow.

【禁止（全画像）】
背景小物、武器、他キャラ、文字、透かし（watermark）、粒子ノイズ、紙テクスチャ、床影・床反射、過度な光沢、強コントラスト、切れフレーミング。

【出力ルール】
- 合計4枚。全画像で同一人物としての一貫性を最優先。
- 差分は「顔の表情のみ」。髪・衣装・体格・ポーズ・画角・線の太さは完全固定。"""
    
    return prompt

def create_base_prompt_without_expression(character: Character) -> str:
    """仕様書フォーマットに基づいたプロンプトを作成"""
    
    # 髪飾りをリスト形式で結合（安全にアクセス）
    hair_accessories = ", ".join(getattr(character.hair, 'accessories', [])) if hasattr(character.hair, 'accessories') and getattr(character.hair, 'accessories', None) else "なし"
    
    # 顔の特徴をリスト形式で結合（安全にアクセス）
    face_marks = ", ".join(getattr(character.face, 'marks', [])) if hasattr(character.face, 'marks') and getattr(character.face, 'marks', None) else "なし"
    
    # アクセサリーをリスト形式で結合（安全にアクセス）
    outfit_accessories = ", ".join(getattr(character.outfit, 'accessories', [])) if hasattr(character.outfit, 'accessories') and getattr(character.outfit, 'accessories', None) else "なし"
    
    prompt = f"""【目的】
同一キャラクターのラノベ風立ち絵を4枚同時に生成する。
4枚は人物・髪・衣装・体格・画角・線のタッチを完全一致させ、顔の表情だけを各枚ごとに変更する。
背景は完全にビビッドなグリーン#00FF00。質感テクスチャや落ち影は一切入れない。全身が頭からつま先までフレーム内に完全に収まること。

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
年齢感: {character.basic.age_appearance}
身長: {character.basic.height_cm}cm前後 / 体格: {character.basic.build}
髪: {character.hair.color}, {character.hair.length}, 前髪: {character.hair.bangs}, スタイル: {character.hair.style}, アクセ: {hair_accessories}
顔: 目色 {character.face.eyes_color}, 目形 {character.face.eyes_shape}, まつ毛 {character.face.eyelashes}, 眉 {character.face.eyebrows}, 口 {character.face.mouth}, 特徴 {face_marks}
服装: {character.outfit.style} / 上 {character.outfit.top} / 下 {character.outfit.bottom} / 小物 {outfit_accessories} / 靴 {character.outfit.shoes}
性格キーワード: {', '.join(character.persona.keywords)} / 役割: {character.persona.role}

【構図・フレーミング（全画像共通・厳守）】
ショット: 全身。頭から足先まで切れずにフレーム内に収める。左右にわずかな余白を取り、中央に配置。
カメラ: 正面、俯瞰なし、50mm相当の自然なパース。レンズ歪みなし。被写界深度は深く、全身にフォーカス。
ポーズ: 直立、肩の力みなし、両腕は体側、指先は自然。足元まで見える。足の向きは正面〜やや内振り程度。
背景: 完全なグリーン (#00FF00)。no texture, no vignette, no gradient, no floor shadow.

【禁止（全画像）】
背景小物、武器、他キャラ、文字、透かし（watermark）、粒子ノイズ、紙テクスチャ、床影・床反射、過度な光沢、強コントラスト、切れフレーミング。

【出力ルール】
- 合計4枚。全画像で同一人物としての一貫性を最優先。
- 差分は「顔の表情のみ」。髪・衣装・体格・ポーズ・画角・線の太さは完全固定。"""
    
    return prompt

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
    
    # 髪飾りがある場合のテキスト（安全にアクセス）
    hair_acc_list = getattr(character.hair, 'accessories', [])
    hair_accessories = f", with {', '.join(hair_acc_list)}" if hair_acc_list else ""
    
    # 顔の特徴がある場合のテキスト（安全にアクセス）
    face_marks_list = getattr(character.face, 'marks', [])
    face_marks = f", with {', '.join(face_marks_list)}" if face_marks_list else ""
    
    # アクセサリーがある場合のテキスト（安全にアクセス）
    outfit_acc_list = getattr(character.outfit, 'accessories', [])
    outfit_accessories = f", wearing {', '.join(outfit_acc_list)}" if outfit_acc_list else ""
    
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

@app.post("/api/generate/simple")
async def generate_images_simple(request: SimpleGenerateRequest):
    """簡略化されたキャラクター画像を生成するエンドポイント"""
    try:
        # 認証情報の確認
        if not credentials:
            logger.error("Credentials are not configured")
            raise HTTPException(
                status_code=500,
                detail="Authentication is not configured properly."
            )
        
        logger.info(f"Generating images for character: {request.character.character_id}")
        
        # 4枚の画像を一度に生成（簡略化版）
        try:
            logger.info("Generating 4 expression variations with simplified data")
            
            # 簡略化された形式用の画像生成関数を呼び出し
            images = generate_images_with_vertex_simple(request.character)
            logger.info(f"Successfully generated {len(images)} images")
        except Exception as e:
            logger.error(f"Failed to generate images: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate images: {str(e)}"
            )
        
        # グリーンバック除去
        processed_images = []
        for i, img_bytes in enumerate(images):
            try:
                processed = remove_green_background(img_bytes)
                processed_images.append(processed)
                logger.info(f"Removed green background from image {i+1}")
            except Exception as e:
                logger.warning(f"Green background removal failed for image {i}: {str(e)}")
                try:
                    processed = remove(Image.open(io.BytesIO(img_bytes)))
                    buf = io.BytesIO()
                    processed.save(buf, format="PNG")
                    processed_images.append(buf.getvalue())
                except Exception as e2:
                    logger.error(f"Fallback background removal also failed: {str(e2)}")
                    processed_images.append(img_bytes)
        
        # 返却形式に応じて処理
        if request.return_type == "base64_list":
            base64_images = [
                base64.b64encode(img).decode("utf-8") 
                for img in processed_images
            ]
            return {
                "images": base64_images,
                "message": f"Successfully generated {len(base64_images)} images"
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

@app.post("/api/generate")
async def generate_images(request: GenerateRequest):
    """キャラクター画像を生成するメインエンドポイント"""
    try:
        # 認証情報の確認
        if not credentials:
            logger.error("Credentials are not configured")
            raise HTTPException(
                status_code=500,
                detail="Authentication is not configured properly."
            )
        
        logger.info(f"Generating images for character: {request.character.character_id}")
        
        # 4枚の画像を一度に生成
        try:
            logger.info("Generating 4 expression variations in single request")
            images = generate_images_with_vertex(request.character)
            logger.info(f"Successfully generated {len(images)} images")
        except Exception as e:
            logger.error(f"Failed to generate images: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate images: {str(e)}"
            )
        
        # グリーンバック除去
        processed_images = []
        for i, img_bytes in enumerate(images):
            try:
                # グリーンを透明にする処理
                processed = remove_green_background(img_bytes)
                processed_images.append(processed)
                logger.info(f"Removed green background from image {i+1}")
            except Exception as e:
                logger.warning(f"Green background removal failed for image {i}: {str(e)}")
                # フォールバック: rembgで背景除去
                try:
                    processed = remove(Image.open(io.BytesIO(img_bytes)))
                    buf = io.BytesIO()
                    processed.save(buf, format="PNG")
                    processed_images.append(buf.getvalue())
                except Exception as e2:
                    logger.error(f"Fallback background removal also failed: {str(e2)}")
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