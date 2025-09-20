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

# Gemini設定 - 環境変数を使わず直接指定
PROJECT_ID = "makeillust"  # プロジェクトIDを直接指定
LOCATION = "global"
MODEL_ID = "gemini-2.5-flash-image-preview"

GENAI_ENDPOINT = (
    f"https://aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/"
    f"publishers/google/models/{MODEL_ID}:generateContent"
)

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
        "api_type": "Vertex AI Gemini 2.5 Flash Image Preview"
    }

def request_gemini_image(
    prompt: str,
    seed: int,
    base_image: Optional[bytes] = None,
    negative_prompt: Optional[str] = None,
    response_modalities: Optional[List[str]] = None,
) -> bytes:
    """Gemini 2.5 Flash Image Previewに画像生成/編集をリクエスト"""

    prompt_with_negative = prompt
    if negative_prompt:
        prompt_with_negative = (
            f"{prompt}\n\n[Negative Prompt]\n"
            f"{negative_prompt}"
        )

    log_payload = {
        "prompt_preview": prompt_with_negative[:200],
        "has_base_image": bool(base_image),
        "seed": seed,
        "location": LOCATION,
    }
    logger.info(f"Gemini image request payload: {json.dumps(log_payload, ensure_ascii=False)}")

    if not credentials:
        raise Exception("Google Cloud default credentials are not configured")

    if hasattr(credentials, 'refresh'):
        credentials.refresh(Request())

    token = credentials.token
    if not token:
        raise Exception("Failed to acquire access token for Gemini API")

    parts: List[Dict[str, Any]] = []
    if base_image:
        parts.append(
            {
                "inline_data": {
                    "mime_type": "image/png",
                    "data": base64.b64encode(base_image).decode("utf-8"),
                }
            }
        )
    parts.append({"text": prompt_with_negative})

    generation_config: Dict[str, Any] = {
        "temperature": 0.4,
        "topP": 0.8,
        "topK": 32,
        "candidateCount": 1,
        "seed": seed,
        "responseMimeType": "image/png",
        "responseModalities": response_modalities or ["IMAGE"],
    }

    request_body = {
        "contents": [
            {
                "role": "user",
                "parts": parts,
            }
        ],
        "generationConfig": generation_config,
        "safetySettings": [
            {
                "category": "HARM_CATEGORY_DANGEROUS",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_SEXUAL",
                "threshold": "BLOCK_ONLY_HIGH"
            }
        ],
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        GENAI_ENDPOINT,
        headers=headers,
        json=request_body,
        timeout=120,
    )

    if response.status_code != 200:
        logger.error(
            "Gemini generateContent error: %s - %s",
            response.status_code,
            response.text,
        )
        raise Exception(f"Gemini API error: {response.status_code} - {response.text}")

    result = response.json()
    for candidate in result.get("candidates", []):
        parts = candidate.get("content", {}).get("parts", [])
        for part in parts:
            data = part.get("inline_data")
            if data and data.get("mime_type", "").startswith("image"):
                return base64.b64decode(data["data"])

    raise Exception(f"Unexpected Gemini response: {result}")

def generate_images_with_vertex_simple(character: SimpleCharacter) -> List[bytes]:
    """簡略化されたキャラクター情報で表情差分ごとに1枚ずつ生成"""
    if not credentials:
        raise HTTPException(status_code=500, detail="Credentials not configured")

    try:
        if credentials and hasattr(credentials, 'refresh'):
            credentials.refresh(Request())

        negative_prompt = "low quality, blurry, watermark, text, signature, multiple people, inconsistent character, white background"

        expressions = [
            ("ニュートラル", """
【各画像の表情差分（顔のみ変更）】
#1: ニュートラル — 穏やかな基準表情
    口: 自然 / 眉: 標準 / 目: 標準"""),
            ("照れながら微笑み", """
【各画像の表情差分（顔のみ変更）】
#2: 照れながら微笑み — 口角をわずかに上げた優しい笑顔
    口: 軽いスマイル / 眉: やや下げ / 目: やや細め"""),
            ("困り顔", """
【各画像の表情差分（顔のみ変更）】
#3: 困り顔 — 申し訳なさそうに眉が寄る
    口: への字（小） / 眉: 内側に寄る / 目: やや細め"""),
            ("むすっ", """
【各画像の表情差分（顔のみ変更）】
#4: むすっ — 拗ねたように正面を見据える
    口: 真一文字 / 眉: 下がる / 目: 標準"""),
        ]

        base_prompt = create_simple_prompt_without_expression(character)
        logger.info(f"Generated base prompt (len={len(base_prompt)}) for character {character.character_id}")

        images: List[bytes] = []

        # 1枚目: テキストから生成
        first_name, first_block = expressions[0]
        first_prompt = f"{base_prompt}\n{first_block}"
        logger.info(f"Creating base image for expression: {first_name}")
        base_image = request_gemini_image(
            first_prompt,
            character.seed,
            negative_prompt=negative_prompt,
        )
        images.append(base_image)

        # 残り3枚: 参照画像を使って表情のみ変更
        for expression_name, expression_block in expressions[1:]:
            logger.info(f"Editing base image for expression: {expression_name}")
            edit_prompt = build_expression_edit_prompt(base_prompt, expression_block)
            try:
                edited = request_gemini_image(
                    edit_prompt,
                    character.seed,
                    base_image=base_image,
                    negative_prompt=negative_prompt,
                )
            except Exception as edit_error:
                logger.warning(
                    "Gemini edit failed for %s, fallback to fresh generation: %s",
                    expression_name,
                    edit_error,
                )
                fallback_prompt = f"{base_prompt}\n{expression_block}"
                edited = request_gemini_image(
                    fallback_prompt,
                    character.seed,
                    negative_prompt=negative_prompt,
                )
            images.append(edited)

        return images

    except Exception as e:
        logger.error(f"Gemini image generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

def generate_images_with_vertex(character: Character) -> List[bytes]:
    """Gemini 2.5 Flash Image Previewで表情差分を生成"""
    if not credentials:
        raise HTTPException(status_code=500, detail="Credentials not configured")
    
    try:
        if credentials and hasattr(credentials, 'refresh'):
            credentials.refresh(Request())

        negative_prompt = "low quality, blurry, watermark, text, signature, multiple people, inconsistent character, white background"

        expressions = [
            ("ニュートラル", """
【各画像の表情差分（顔のみ変更）】
#1: ニュートラル — 穏やかな基準表情
    口: 自然 / 眉: 標準 / 目: 標準"""),
            ("照れながら微笑み", """
【各画像の表情差分（顔のみ変更）】
#2: 照れながら微笑み — 口角をわずかに上げた優しい笑顔
    口: 軽いスマイル / 眉: やや下げ / 目: やや細め"""),
            ("困り顔", """
【各画像の表情差分（顔のみ変更）】
#3: 困り顔 — 申し訳なさそうに眉が寄る
    口: への字（小） / 眉: 内側に寄る / 目: やや細め"""),
            ("むすっ", """
【各画像の表情差分（顔のみ変更）】
#4: むすっ — 拗ねたように正面を見据える
    口: 真一文字 / 眉: 下がる / 目: 標準"""),
        ]

        base_prompt = create_base_prompt_without_expression(character)
        logger.info(f"Generated base prompt (len={len(base_prompt)}) for character {character.character_id}")

        images: List[bytes] = []

        # 1枚目: テキストから生成
        first_name, first_block = expressions[0]
        first_prompt = f"{base_prompt}\n{first_block}"
        logger.info(f"Creating base image for expression: {first_name}")
        base_image = request_gemini_image(
            first_prompt,
            character.seed,
            negative_prompt=negative_prompt,
        )
        images.append(base_image)

        # 残り3枚: 参照画像を使って表情のみ変更
        for expression_name, expression_block in expressions[1:]:
            logger.info(f"Editing base image for expression: {expression_name}")
            edit_prompt = build_expression_edit_prompt(base_prompt, expression_block)
            try:
                edited = request_gemini_image(
                    edit_prompt,
                    character.seed,
                    base_image=base_image,
                    negative_prompt=negative_prompt,
                )
            except Exception as edit_error:
                logger.warning(
                    "Gemini edit failed for %s, fallback to fresh generation: %s",
                    expression_name,
                    edit_error,
                )
                fallback_prompt = f"{base_prompt}\n{expression_block}"
                edited = request_gemini_image(
                    fallback_prompt,
                    character.seed,
                    negative_prompt=negative_prompt,
                )
            images.append(edited)

        return images

    except Exception as e:
        logger.error(f"Gemini image generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

def remove_green_background(image_bytes: bytes) -> bytes:
    """グリーンバックを透明にする"""
    try:
        # rembgで背景を除去（透過PNGを返す）
        return remove(image_bytes)
    except Exception as primary_error:
        logger.warning(f"rembg removal failed, falling back to manual threshold: {primary_error}")
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
            data = img.getdata()
            new_data = []
            green_threshold = 90
            red_threshold = 130
            blue_threshold = 130
            for r, g, b, a in data:
                if g > green_threshold and r < red_threshold and b < blue_threshold:
                    new_data.append((r, g, b, 0))
                else:
                    new_data.append((r, g, b, a))
            img.putdata(new_data)
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            return buffer.getvalue()
        except Exception as fallback_error:
            logger.error(f"Green background removal error: {fallback_error}")
            raise

def create_simple_prompt_without_expression(character: SimpleCharacter) -> str:
    """簡略化されたキャラクター情報から仕様書フォーマットのプロンプトを作成"""
    
    # デバッグ: 受け取ったキャラクター情報をログ出力
    logger.info(f"Creating prompt for character: age={character.age}, hair={character.hair}, outfit={character.outfit}")
    
    prompt = f"""【目的】
同一キャラクターのラノベ風立ち絵を1枚生成する。
この画像は指定された表情以外の要素を完全に固定し、画面内には必ず単一のキャラクターのみを描写する。
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
- この画像は単一の全身立ち絵1枚。フレーム内の人物は一人のみ。
- 差分は「顔の表情のみ」（この後ろに続く表情指定に従う）。髪・衣装・体格・ポーズ・画角・線の太さは完全固定。
- 追加のキャラクター、複数人、反射像、鏡像の描写は禁止。"""
    
    return prompt

def build_expression_edit_prompt(base_prompt: str, expression_block: str) -> str:
    """既存画像を参照して表情のみ変更するための追加指示を付与"""

    return (
        f"{base_prompt}\n{expression_block}\n\n"
        "【追加指示】参照画像として添付された既存の立ち絵を使用し、"
        "髪型・衣装・体格・ポーズ・照明・背景・線のタッチは一切変更せず、"
        "顔の表情だけを指定された内容に差し替える。ビフォーアフターで人物は完全に同一であり、"
        "追加の人物や構図変更は厳禁。"
    )

def create_base_prompt_without_expression(character: Character) -> str:
    """仕様書フォーマットに基づいたプロンプトを作成"""
    
    # 髪飾りをリスト形式で結合（安全にアクセス）
    hair_accessories = ", ".join(getattr(character.hair, 'accessories', [])) if hasattr(character.hair, 'accessories') and getattr(character.hair, 'accessories', None) else "なし"
    
    # 顔の特徴をリスト形式で結合（安全にアクセス）
    face_marks = ", ".join(getattr(character.face, 'marks', [])) if hasattr(character.face, 'marks') and getattr(character.face, 'marks', None) else "なし"
    
    # アクセサリーをリスト形式で結合（安全にアクセス）
    outfit_accessories = ", ".join(getattr(character.outfit, 'accessories', [])) if hasattr(character.outfit, 'accessories') and getattr(character.outfit, 'accessories', None) else "なし"
    
    prompt = f"""【目的】
同一キャラクターのラノベ風立ち絵を1枚生成する。
この画像は指定された表情以外の要素を完全に固定し、画面内には必ず単一のキャラクターのみを描写する。
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
- この画像は単一の全身立ち絵1枚。フレーム内の人物は一人のみ。
- 差分は「顔の表情のみ」（この後ろに続く表情指定に従う）。髪・衣装・体格・ポーズ・画角・線の太さは完全固定。
- 追加のキャラクター、複数人、反射像、鏡像の描写は禁止。"""
    
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
        
        # 4つの表情バリエーションを順次生成（簡略化版）
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
        
        # 4つの表情バリエーションを順次生成
        try:
            logger.info("Generating 4 expression variations sequentially")
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
