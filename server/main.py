import os
import io
import base64
import zipfile
import logging
import json
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import FastAPI, HTTPException, Response, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import requests
from rembg import remove
from PIL import Image
from google.auth import default
try:
    from google.auth.transport.requests import Request
except ImportError:
    # Fallback if google-auth-httplib2 is not installed
    from google.auth.transport import requests as auth_requests
    Request = auth_requests.Request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 起動ログ
logger.info("Starting Standing Set Backend Service...")

# Gemini設定 - 環境変数を使わず直接指定
PROJECT_ID = "812480532939"  # 実際のGCPプロジェクトIDを直接指定
LOCATION = "global"
MODEL_ID = "gemini-2.5-flash-image-preview"

GENAI_ENDPOINT = (
    f"https://aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/"
    f"publishers/google/models/{MODEL_ID}:generateContent"
)

logger.info(f"Configured endpoint: {GENAI_ENDPOINT}")

# 認証情報を取得
credentials = None
try:
    credentials, project = default()
    logger.info(f"Using default credentials for project: {project}")
except Exception as e:
    logger.warning(f"Failed to get default credentials on startup (will retry on request): {e}")
    # 起動時に失敗しても続行

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

class EmoCharacter(BaseModel):
    character_id: str = Field(default="emo_001", description="キャラクターID")
    seed: int = Field(default=123456789, description="シード値")
    height: str = Field(..., description="身長: small/medium/tall")
    hair: str = Field(..., description="髪型と髪色（例：黒のロングストレート）")
    eyes: str = Field(..., description="目の形と色（例：大きい青い目）")
    outfit: str = Field(..., description="服装（例：メイド服、カジュアル）")

class FantasyCharacter(BaseModel):
    character_id: str = Field(default="fantasy_001", description="キャラクターID")
    seed: int = Field(default=123456789, description="シード値")
    height: str = Field(..., description="頭身: small/medium/tall")
    hair_length: str = Field(..., description="髪の長さ（例：long、short、medium）")
    hair_color: str = Field(..., description="髪色（例：silver、blonde、black）")
    hair_style: str = Field(..., description="髪型（例：straight、wavy、twintails）")
    outfit: str = Field(..., description="服装（例：knight armor、mage robe、elegant dress）")
    eye_shape: str = Field(..., description="瞳の形（例：large、narrow、almond-shaped）")
    eye_color: str = Field(..., description="瞳の色（例：blue、red、heterochromia）")
    expression: str = Field(..., description="表情（例：confident、mysterious、gentle）")

class SimpleGenerateRequest(BaseModel):
    character: Optional[SimpleCharacter] = Field(default=None, description="通常モード用キャラクター")
    return_type: str = Field(default="base64_list", description="返却形式: 'zip' or 'base64_list'")
    mode: str = Field(default="normal", description="生成モード: 'normal' or 'emo' or 'fantasy'")  # モード追加
    emo_character: Optional[EmoCharacter] = Field(default=None, description="エモモード用キャラクター")
    fantasy_character: Optional[FantasyCharacter] = Field(default=None, description="ファンタジーモード用キャラクター")

@app.get("/")
def root():
    """ルートエンドポイント"""
    return {"message": "Standing Set Backend Service", "status": "running"}

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
        "port": os.getenv("PORT", "8080"),
        "api_type": "Vertex AI Gemini 2.5 Flash Image Preview"
    }

@app.post("/api/depth-estimation")
async def estimate_depth(image_file: Optional[UploadFile] = File(None), use_depth_anything: bool = False):
    """
    画像の深度推定を行い、視差レイヤー情報を生成
    use_depth_anything=Trueの場合、Depth Anything V2を使用（より正確な深度推定）
    """
    try:
        # 認証情報の確認
        if not credentials:
            raise HTTPException(status_code=500, detail="Credentials not configured")
        
        # 画像データの読み込み
        if image_file:
            image_bytes = await image_file.read()
        else:
            # デフォルトでhaikei2.pngを使用 - Cloud Run環境用のパスも試す
            possible_paths = [
                "/app/haikei2.png",  # Docker container path
                "./haikei2.png",     # Current directory
                "/Users/dcenter/Desktop/make_illust/haikei2.png"  # Local development
            ]
            
            image_bytes = None
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        image_bytes = f.read()
                    break
            
            if not image_bytes:
                # フォールバックとして、ダミーの深度情報を返す
                logger.warning("Default image not found, using fallback depth layers")
                return JSONResponse(content={
                    "status": "success",
                    "depth_layers": get_default_depth_layers(),
                    "parallax_config": generate_parallax_config(get_default_depth_layers())
                })
        
        # 深度推定方法の選択
        if use_depth_anything:
            # Depth Anything V2を使用（より正確な深度推定）
            try:
                from server.depth_anything import estimate_depth_with_depth_anything
                logger.info("Using Depth Anything V2 for depth estimation")
                
                # Hugging Face APIトークン（環境変数から取得）
                hf_token = os.getenv("HUGGINGFACE_TOKEN")
                
                depth_result = estimate_depth_with_depth_anything(
                    image_bytes,
                    hf_token=hf_token,
                    use_local=False  # APIを使用
                )
                
                return JSONResponse(content={
                    "status": "success",
                    "depth_layers": depth_result,
                    "parallax_config": generate_parallax_config(depth_result),
                    "method": "depth_anything_v2"
                })
                
            except ImportError as e:
                logger.warning(f"Depth Anything module not available: {e}, falling back to Gemini")
                use_depth_anything = False
            except Exception as e:
                logger.error(f"Depth Anything error: {e}, falling back to Gemini")
                use_depth_anything = False
        
        # Gemini 1.5 Flashで深度分析を行う（デフォルトまたはフォールバック）
        if not use_depth_anything:
            img = Image.open(io.BytesIO(image_bytes))
            img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            depth_layers = analyze_depth_with_gemini(image_base64)
            
            return JSONResponse(content={
                "status": "success",
                "depth_layers": depth_layers,
                "parallax_config": generate_parallax_config(depth_layers),
                "method": "gemini_1.5_flash"
            })
        
    except Exception as e:
        logger.error(f"Depth estimation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Depth estimation failed: {str(e)}")

def analyze_depth_with_gemini(image_base64: str) -> Dict[str, Any]:
    """
    Gemini 1.5 Flashを使用して画像の深度を分析し、レイヤー情報を生成
    被写体（人物）を検知して適切な深度情報を返す
    """
    if not credentials:
        logger.warning("Credentials not configured, using default depth layers")
        return get_default_depth_layers()
    
    try:
        # 認証トークンの取得
        if hasattr(credentials, 'refresh'):
            credentials.refresh(Request())
        
        token = getattr(credentials, 'token', None)
        if not token:
            logger.warning("Failed to acquire access token, using default depth layers")
            return get_default_depth_layers()
        
        # Gemini 1.5 Flash（画像理解対応）のエンドポイント
        vision_endpoint = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/gemini-1.5-flash:generateContent"
        
        # 被写体検知と深度分析用のプロンプト
        prompt = """この画像を分析して、以下の情報をJSON形式で提供してください：

1. 人物や主要な被写体の検出
2. 各被写体の画像内での位置（前景、中景、背景）
3. 視差効果のための深度レイヤー情報

特に注目すべき点：
- 人物が存在する場合、その位置と大きさ
- 人物の服装、髪型、ポーズなどの特徴
- 背景要素（空、海、ビーチ、建物など）
- 各要素の相対的な深度

以下の形式でJSONを返してください：
{
  "subject_detection": {
    "has_person": true/false,
    "person_position": "foreground/midground/background",
    "person_description": "検出された人物の説明",
    "person_bounds": {
      "x": 0-100（画像幅に対する％）,
      "y": 0-100（画像高さに対する％）,
      "width": 0-100,
      "height": 0-100
    }
  },
  "layers": [
    {
      "name": "background",
      "depth": 70-100,
      "content": "背景の内容（空、海など）",
      "parallax_strength": "strong",
      "movement": "horizontal",
      "scale": 1.2,
      "blur": 2,
      "opacity": 0.9,
      "animation_speed": 30
    },
    {
      "name": "midground", 
      "depth": 30-70,
      "content": "中景の内容",
      "parallax_strength": "medium",
      "movement": "both",
      "scale": 1.1,
      "blur": 0.5,
      "opacity": 0.95,
      "animation_speed": 25
    },
    {
      "name": "foreground",
      "depth": 0-30,
      "content": "前景の内容（人物など）",
      "parallax_strength": "weak",
      "movement": "horizontal",
      "scale": 1.0,
      "blur": 0,
      "opacity": 1.0,
      "animation_speed": 20
    }
  ]
}"""
        
        request_body = {
            "contents": [{
                "role": "user",
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": image_base64
                        }
                    },
                    {"text": prompt}
                ]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.95,
                "topK": 40,
                "candidateCount": 1,
                "maxOutputTokens": 2048
            }
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Calling Gemini 1.5 Flash for image analysis: {vision_endpoint}")
        response = requests.post(
            vision_endpoint,
            headers=headers,
            json=request_body,
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"Gemini Vision API error: {response.status_code} - {response.text}")
            return get_default_depth_layers()
        
        result = response.json()
        
        # レスポンスから深度情報を抽出
        try:
            content = result['candidates'][0]['content']['parts'][0]['text']
            logger.info(f"Gemini Vision response preview: {content[:200]}...")
            
            # JSONを抽出して解析
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                depth_data = json.loads(json_match.group())
                logger.info(f"Successfully parsed depth data with subject detection: {depth_data.get('subject_detection', {}).get('has_person', False)}")
                return depth_data
            else:
                logger.warning("No JSON found in Gemini response")
                return get_default_depth_layers()
                
        except Exception as e:
            logger.warning(f"Failed to parse Gemini response: {e}")
            return get_default_depth_layers()
            
    except Exception as e:
        logger.error(f"Error in analyze_depth_with_gemini: {e}")
        return get_default_depth_layers()

def get_default_depth_layers() -> Dict[str, Any]:
    """
    デフォルトの深度レイヤー情報を返す
    """
    return {
        "layers": [
            {
                "name": "background",
                "depth": 90,
                "parallax_strength": "strong",
                "movement": "horizontal",
                "scale": 1.3,
                "blur": 3,
                "opacity": 0.8,
                "animation_speed": 30
            },
            {
                "name": "midground",
                "depth": 50,
                "parallax_strength": "medium",
                "movement": "both",
                "scale": 1.1,
                "blur": 1,
                "opacity": 0.9,
                "animation_speed": 25
            },
            {
                "name": "foreground",
                "depth": 10,
                "parallax_strength": "weak",
                "movement": "horizontal",
                "scale": 1.0,
                "blur": 0,
                "opacity": 1.0,
                "animation_speed": 20
            }
        ]
    }

def generate_parallax_config(depth_layers: Dict[str, Any]) -> Dict[str, Any]:
    """
    深度情報から視差アニメーション設定を生成
    """
    config = {
        "layers": [],
        "animation_type": "time-based",
        "global_speed": 1.0
    }
    
    for layer in depth_layers.get("layers", []):
        layer_config = {
            "id": layer["name"],
            "depth": layer["depth"],
            "animations": []
        }
        
        # 深度に基づいて視差の動きを計算
        depth_factor = layer["depth"] / 100
        
        # 水平移動のアニメーション
        if layer["movement"] in ["horizontal", "both"]:
            layer_config["animations"].append({
                "type": "translateX",
                "amplitude": 30 * depth_factor,  # 深い層ほど大きく動く
                "frequency": 1 / layer["animation_speed"],
                "phase": 0
            })
        
        # 垂直移動のアニメーション
        if layer["movement"] in ["vertical", "both"]:
            layer_config["animations"].append({
                "type": "translateY",
                "amplitude": 20 * depth_factor,
                "frequency": 1 / (layer["animation_speed"] * 1.2),
                "phase": 0.25  # 位相をずらして自然な動きに
            })
        
        # スケールアニメーション（呼吸効果）
        layer_config["animations"].append({
            "type": "scale",
            "amplitude": 0.05 * (1 - depth_factor),  # 手前の層ほど大きくスケール変化
            "frequency": 1 / (layer["animation_speed"] * 2),
            "phase": 0.5
        })
        
        config["layers"].append(layer_config)
    
    return config

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
        "project_id": PROJECT_ID,
        "endpoint": GENAI_ENDPOINT[:100]
    }
    logger.info(f"Gemini image request payload: {json.dumps(log_payload, ensure_ascii=False)}")

    if not credentials:
        logger.error("Credentials is None in request_gemini_image")
        raise Exception("Google Cloud default credentials are not configured")

    if hasattr(credentials, 'refresh'):
        logger.info("Refreshing credentials in request_gemini_image...")
        credentials.refresh(Request())
        logger.info(f"After refresh, has token: {hasattr(credentials, 'token')}")

    token = getattr(credentials, 'token', None)
    if not token:
        logger.error(f"Failed to get token. Credentials type: {type(credentials).__name__}")
        logger.error(f"Credentials attributes: {dir(credentials)}")
        raise Exception("Failed to acquire access token for Gemini API")
    
    logger.info(f"Token acquired successfully (length: {len(token)}...{token[-10:] if len(token) > 10 else token})")

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

    # Gemini 2.5 Flash Image Previewでは TEXT+IMAGE の組み合わせが必要
    effective_modalities = response_modalities if response_modalities else ["TEXT", "IMAGE"]

    generation_config: Dict[str, Any] = {
        "temperature": 0.3,  # Lower temperature for more consistent results
        "topP": 0.85,  # Slightly higher for better quality
        "topK": 40,  # Increased for more options
        "candidateCount": 1,
        "seed": seed,
        # "responseMimeType": "image/png",  # Not supported for image generation
        "responseModalities": effective_modalities,  # TEXT+IMAGE が必要
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
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
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
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_ONLY_HIGH"
            }
        ],
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    logger.info(f"Sending request to Gemini API endpoint: {GENAI_ENDPOINT}")
    logger.info(f"Request headers (without token): Content-Type: {headers.get('Content-Type')}")
    
    response = requests.post(
        GENAI_ENDPOINT,
        headers=headers,
        json=request_body,
        timeout=120,
    )

    logger.info(f"Gemini API response status: {response.status_code}")
    
    if response.status_code != 200:
        logger.error(
            "Gemini generateContent error: %s - Full response: %s",
            response.status_code,
            response.text  # Show full error for debugging
        )
        # Try to parse error for more details
        try:
            error_json = response.json()
            logger.error(f"Error JSON parsed: {json.dumps(error_json, indent=2, ensure_ascii=False)}")
            
            # Check for specific error messages
            if "error" in error_json:
                error_msg = error_json.get("error", {})
                if isinstance(error_msg, dict):
                    logger.error(f"Error message: {error_msg.get('message', 'No message')}")
                    logger.error(f"Error code: {error_msg.get('code', 'No code')}")
                    logger.error(f"Error status: {error_msg.get('status', 'No status')}")
                    
                    # Check for specific validation errors
                    if "Invalid value" in str(error_msg.get('message', '')):
                        logger.error("Validation error detected - checking request payload")
                        logger.error(f"Request body was: {json.dumps(request_body, indent=2, ensure_ascii=False)[:2000]}")
        except Exception as parse_error:
            logger.error(f"Failed to parse error response: {parse_error}")
        
        # Return more specific error based on status code
        if response.status_code == 400:
            error_detail = "Bad request to Gemini API. "
            if "safety_setting" in response.text:
                error_detail += "Safety settings configuration error. "
            elif "Invalid value" in response.text:
                error_detail += "Invalid parameter values in request. "
            error_detail += response.text[:500]
            raise HTTPException(status_code=400, detail=error_detail)
        elif response.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="Authentication failed. Please check API credentials."
            )
        elif response.status_code == 403:
            raise HTTPException(
                status_code=403,
                detail="Permission denied. Please check API permissions and quotas."
            )
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Gemini API error: {response.status_code} - {response.text[:500]}"
            )

    result = response.json()
    logger.info(f"Gemini response structure: candidates={len(result.get('candidates', []))}")
    
    for candidate in result.get("candidates", []):
        parts = candidate.get("content", {}).get("parts", [])
        logger.info(f"Parts in candidate: {len(parts)}")
        
        for part in parts:
            # Gemini API uses camelCase: inlineData, not inline_data
            data = part.get("inlineData") or part.get("inline_data")  # Check both for compatibility
            if data and data.get("mimeType", "").startswith("image"):
                logger.info("Found image in response")
                return base64.b64decode(data["data"])
            elif data and data.get("mime_type", "").startswith("image"):
                logger.info("Found image in response (snake_case)")
                return base64.b64decode(data["data"])

    logger.error(f"No image found in Gemini response. Full response: {json.dumps(result, indent=2)[:1000]}")
    raise Exception(f"No image found in Gemini response")

def generate_images_with_vertex_simple(character: SimpleCharacter) -> List[bytes]:
    """簡略化されたキャラクター情報で表情差分ごとに1枚ずつ生成"""
    if not credentials:
        logger.error("Credentials are None - not configured at all")
        raise HTTPException(status_code=500, detail="Credentials not configured")

    try:
        logger.info(f"Starting image generation for character {character.character_id}")
        logger.info(f"Credentials type: {type(credentials).__name__}")
        
        if credentials and hasattr(credentials, 'refresh'):
            logger.info("Refreshing credentials...")
            credentials.refresh(Request())
            logger.info(f"Token acquired: {bool(getattr(credentials, 'token', None))}")

        negative_prompt = "low quality, blurry, dark, underexposed, dim lighting, watermark, text, signature, multiple people, inconsistent character, white background, green outline, green edge, green spill, green fringe, green glow, green halo, chromatic aberration, color bleeding, color fringing, artifacts around edges, fuzzy edges, blurred edges"

        expressions = [
            ("微笑み", """
【各画像の表情差分（顔のみ変更）】
#1: 微笑み — 口角をわずかに上げた優しい笑顔
    口: 軽いスマイル / 眉: やや下げ / 目: やや細め"""),
            ("ニュートラル", """
【各画像の表情差分（顔のみ変更）】
#2: ニュートラル — 穏やかな基準表情
    口: 自然 / 眉: 標準 / 目: 標準"""),
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

        # 残り3枚: 並列処理で参照画像を使って表情のみ変更
        def generate_expression(expression_data):
            expression_name, expression_block = expression_data
            logger.info(f"Starting parallel generation for expression: {expression_name}")
            edit_prompt = build_expression_edit_prompt(base_prompt, expression_block)
            try:
                result = request_gemini_image(
                    edit_prompt,
                    character.seed,
                    base_image=base_image,
                    negative_prompt=negative_prompt,
                )
                logger.info(f"Successfully generated expression: {expression_name}")
                return result
            except Exception as edit_error:
                logger.warning(
                    "Gemini edit failed for %s, fallback to fresh generation: %s",
                    expression_name,
                    edit_error,
                )
                fallback_prompt = f"{base_prompt}\n{expression_block}"
                return request_gemini_image(
                    fallback_prompt,
                    character.seed,
                    negative_prompt=negative_prompt,
                )
        
        # ThreadPoolExecutorで並列実行（最大3スレッドで同時実行）
        logger.info("Starting parallel generation for 3 expression variations")
        with ThreadPoolExecutor(max_workers=3) as executor:
            # 各表情の生成タスクをサブミット
            future_to_expression = {
                executor.submit(generate_expression, exp_data): idx 
                for idx, exp_data in enumerate(expressions[1:], start=1)
            }
            
            # 結果を順番どおりに格納するための辞書
            results = {}
            
            # 完了した順に結果を取得
            for future in as_completed(future_to_expression):
                idx = future_to_expression[future]
                try:
                    result = future.result(timeout=120)  # 120秒のタイムアウト
                    results[idx] = result
                    logger.info(f"Expression {idx} generated successfully")
                except Exception as e:
                    logger.error(f"Expression {idx} generation failed: {e}")
                    raise HTTPException(status_code=500, detail=f"Failed to generate expression {idx}: {str(e)}")
            
            # 順番どおりにimagesリストに追加
            for idx in sorted(results.keys()):
                images.append(results[idx])
        
        logger.info(f"All {len(images)} images generated successfully")

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

        negative_prompt = "low quality, blurry, dark, underexposed, dim lighting, watermark, text, signature, multiple people, inconsistent character, white background, green outline, green edge, green spill, green fringe, green glow, green halo, chromatic aberration, color bleeding, color fringing, artifacts around edges, fuzzy edges, blurred edges"

        expressions = [
            ("微笑み", """
【各画像の表情差分（顔のみ変更）】
#1: 微笑み — 口角をわずかに上げた優しい笑顔
    口: 軽いスマイル / 眉: やや下げ / 目: やや細め"""),
            ("ニュートラル", """
【各画像の表情差分（顔のみ変更）】
#2: ニュートラル — 穏やかな基準表情
    口: 自然 / 眉: 標準 / 目: 標準"""),
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

        # 残り3枚: 並列処理で参照画像を使って表情のみ変更
        def generate_expression(expression_data):
            expression_name, expression_block = expression_data
            logger.info(f"Starting parallel generation for expression: {expression_name}")
            edit_prompt = build_expression_edit_prompt(base_prompt, expression_block)
            try:
                result = request_gemini_image(
                    edit_prompt,
                    character.seed,
                    base_image=base_image,
                    negative_prompt=negative_prompt,
                )
                logger.info(f"Successfully generated expression: {expression_name}")
                return result
            except Exception as edit_error:
                logger.warning(
                    "Gemini edit failed for %s, fallback to fresh generation: %s",
                    expression_name,
                    edit_error,
                )
                fallback_prompt = f"{base_prompt}\n{expression_block}"
                return request_gemini_image(
                    fallback_prompt,
                    character.seed,
                    negative_prompt=negative_prompt,
                )
        
        # ThreadPoolExecutorで並列実行（最大3スレッドで同時実行）
        logger.info("Starting parallel generation for 3 expression variations")
        with ThreadPoolExecutor(max_workers=3) as executor:
            # 各表情の生成タスクをサブミット
            future_to_expression = {
                executor.submit(generate_expression, exp_data): idx 
                for idx, exp_data in enumerate(expressions[1:], start=1)
            }
            
            # 結果を順番どおりに格納するための辞書
            results = {}
            
            # 完了した順に結果を取得
            for future in as_completed(future_to_expression):
                idx = future_to_expression[future]
                try:
                    result = future.result(timeout=120)  # 120秒のタイムアウト
                    results[idx] = result
                    logger.info(f"Expression {idx} generated successfully")
                except Exception as e:
                    logger.error(f"Expression {idx} generation failed: {e}")
                    raise HTTPException(status_code=500, detail=f"Failed to generate expression {idx}: {str(e)}")
            
            # 順番どおりにimagesリストに追加
            for idx in sorted(results.keys()):
                images.append(results[idx])
        
        logger.info(f"All {len(images)} images generated successfully")

        return images

    except Exception as e:
        logger.error(f"Gemini image generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

def remove_green_background(image_bytes: bytes) -> bytes:
    """グリーンバックを透明にする - エッジのモヤを除去"""
    try:
        # Step 1: rembgで初期背景除去
        logger.info("Starting rembg background removal")
        removed = remove(image_bytes, alpha_matting=True, alpha_matting_foreground_threshold=240, alpha_matting_background_threshold=50)
        
        # Step 2: PILで追加のクリーンアップ処理
        img = Image.open(io.BytesIO(removed)).convert("RGBA")
        width, height = img.size
        pixels = img.load()
        
        # エッジのグリーンアーティファクトを除去
        for y in range(height):
            for x in range(width):
                r, g, b, a = pixels[x, y]
                
                # 半透明部分のグリーン成分を調整
                if 0 < a < 255:
                    # グリーン優勢なピクセルを検出
                    if g > r * 1.2 and g > b * 1.2:
                        # グリーンを減衰させる
                        new_g = int((r + b) / 2)
                        pixels[x, y] = (r, new_g, b, a)
                    
                    # 透明度が低い場合は完全に透明にする
                    if a < 30:
                        pixels[x, y] = (r, g, b, 0)
                    # 透明度が高い場合は完全に不透明にする
                    elif a > 225:
                        pixels[x, y] = (r, g, b, 255)
                
                # 完全に不透明なグリーンっぽいピクセルもチェック
                elif a == 255:
                    # 明らかなグリーンエッジを検出
                    if g > r * 1.5 and g > b * 1.5 and g > 150:
                        # 隣接ピクセルをチェックして、エッジかどうか判定
                        is_edge = False
                        for dx in [-1, 0, 1]:
                            for dy in [-1, 0, 1]:
                                if dx == 0 and dy == 0:
                                    continue
                                nx, ny = x + dx, y + dy
                                if 0 <= nx < width and 0 <= ny < height:
                                    _, _, _, na = pixels[nx, ny]
                                    if na < 255:
                                        is_edge = True
                                        break
                            if is_edge:
                                break
                        
                        # エッジのグリーンを調整
                        if is_edge:
                            new_g = int((r + b) / 2)
                            pixels[x, y] = (r, new_g, b, a)
        
        # Step 3: 結果を保存
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Enhanced background removal failed: {e}")
        # フォールバック処理
        try:
            return remove(image_bytes)  # 基本的なrembg処理にフォールバック
        except Exception as fallback_error:
            logger.error(f"Fallback removal also failed: {fallback_error}")
            # 最終フォールバック: オリジナル画像を返す
            return image_bytes

def create_simple_prompt_without_expression(character: SimpleCharacter) -> str:
    """簡略化されたキャラクター情報から仕様書フォーマットのプロンプトを作成"""
    
    # デバッグ: 受け取ったキャラクター情報をログ出力
    logger.info(f"Creating prompt for character: age={character.age}, hair={character.hair}, outfit={character.outfit}")
    
    prompt = f"""【目的】
同一キャラクターのラノベ風立ち絵を1枚生成する。
この画像は指定された表情以外の要素を完全に固定し、画面内には必ず単一のキャラクターのみを描写する。

【重要】背景は均一なクロマキーグリーン (pure chroma key green background, RGB(0,255,0), #00FF00)。
キャラクターの輪郭線は背景から完全に独立し、グリーンのにじみや反射は一切なし。
Clean, sharp edge separation between character and green screen. No green color spill, fringing or halo around character.
Bright, well-lit character with high-key lighting to prevent dark/underexposed results.
Ensure character is bright and clearly visible with good contrast against green background.
質感テクスチャや落ち影は一切入れない。全身が頭からつま先までフレーム内に完全に収まること。

【色調（数値を使わない指定）】
overall color grading: bright pale tones, light grayish tones, soft muted pastel tones.
airy and bright atmosphere, emotional pastel look with good visibility.
no vivid or highly saturated colors, but maintain sufficient brightness.
medium-contrast tonal range for clear visibility, avoid crushed blacks and maintain bright whites.
Ensure overall bright exposure (high-key lighting) to prevent dark or muddy results.

【線（輪郭）】
outline color: clear, desaturated cool gray; not pure black but visible against green.
outer contour lines: bold and clean to create sharp silhouette against green background.
inner facial/detail lines: finer and lighter gray.
consistent, clean, sharp lines with no fuzzy edges; no sketchy strokes or messy hatching.
Ensure crisp, well-defined edges for clean chromakey extraction.

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
背景: 完全に均一な純粋グリーンスクリーン (RGB: 0, 255, 0 / #00FF00)。
輪郭線とグリーン背景の境界を明確に分離。エッジにグリーンのにじみなし。
no texture, no vignette, no gradient, no floor shadow, no green spill on character edges.

【禁止（全画像）】
背景小物、武器、他キャラ、文字、透かし（watermark）、粒子ノイズ、紙テクスチャ、床影・床反射、過度な光沢、強コントラスト、切れフレーミング。

【出力ルール】
- この画像は単一の全身立ち絵1枚。フレーム内の人物は一人のみ。
- 差分は「顔の表情のみ」（この後ろに続く表情指定に従う）。髪・衣装・体格・ポーズ・画角・線の太さは完全固定。
- 追加のキャラクター、複数人、反射像、鏡像の描写は禁止。"""
    
    return prompt

def create_emo_prompt(character: EmoCharacter) -> str:
    """エモ用のプロンプト生成（final_anime_prompt_v6.mdベース）"""
    # heightの値を適切に変換
    height_map = {
        "small": "small",
        "medium": "medium", 
        "tall": "tall",
        "小さい": "small",
        "普通": "medium",
        "大きめ": "tall"
    }
    height = height_map.get(character.height.lower(), "medium")
    
    prompt = f"""Professional anime illustration with masterpiece quality and absurdres detail level for game sprite use, featuring a single girl with {character.hair} and {character.eyes} wearing {character.outfit} with {height} proportions, standing in perfectly upright vertical position suitable for game character sprite with no head tilt or body lean, full body pose against a pure black background that must remain completely black without any gray tones, where these user specifications take absolute priority and must be followed exactly as written, with the character rendered in a sophisticated flat coloring style that creates depth entirely through strategic brightness gradients rather than traditional shadows, starting with the character's proportions which vary based on the HEIGHT parameter where small creates exactly 5 head tall petite figure with youthful innocent features and noticeably shorter stature maintaining cuteness without explicit childish elements, tall creates elegant 6.5 head tall proportions with elongated elegant limbs and mature sophisticated features, and medium or unspecified creates standard 5.5-6 head tall proportions with balanced teenage appearance, ensuring the figure maintains realistic anime proportions absolutely never becoming chibi or super-deformed regardless of height selection, with properly proportioned limbs where legs comprise 45% of total height for all builds, implementing absolutely mandatory comprehensive gradient-based rendering system where EVERY single element from hair to clothing to accessories MUST show dramatic 30-40% brightness variations to create dimensionality or the image is considered failed, specifically the hair must transition from 40% brightness at the roots through 55% in the mid-sections to 70% at the tips with individual strand groups varying by 10% brightness to create natural volume without any cel shading, using blue-tinted dark gray base colors like #1A1A2E or #16213E for dark hair rather than pure black to maintain the soft aesthetic, while clothing follows an absolute mandatory layering system where EVERY single piece shows brightness gradients: shirts/tops must be 95% brightness at shoulders gradually darkening to 55% at waist creating 40% variation, skirts must be 90% brightness at waistband darkening to 50% at hem for clear vertical depth, sleeves transitioning from 95% at shoulders to 60% at wrists, aprons and outer layers following same top-to-bottom gradient rules, with the frontmost complete layer at overall 95% brightness, second layer at 80%, third at 70%, fourth at 60%, and every fold/crease showing additional 20% darkening, creating clear depth hierarchy without breaking flat coloring rule, with gradient effect so prominent that viewer can immediately see the brightness variation on every piece of clothing, if any clothing appears uniformly colored the image is failed, applying this same gradient principle to ALL clothing elements not just hair, where every piece of clothing must show clear brightness gradients creating dimensional appearance purely through brightness variation, with shoes and feet showing 40% darker brightness at ground contact points transitioning smoothly upward, using regular footwear appropriate to the outfit, using the established palette of powder blue #E0F4FF, baby pink #FFE8F0, pale lavender #E6E0F0, and mint green #F0FFF8, all maintaining 90-95% brightness with only 15-25% saturation to achieve the characteristic milky washed-out appearance, ensuring that traditional black elements in clothing like maid outfits are replaced with dark blue-gray #2C3E50 while maintaining the outfit's recognizable silhouette, for casual/streetwear use full pastel palette, BUT for maid outfits keep traditional black as dark blue-gray #2C3E50 NOT pastel, whites stay cream #FFF8F0, incorporating minimum 4-5 overlapping clothing layers to create depth through brightness variation alone, each layer featuring different fabric textures indicated solely through subtle color and brightness shifts rather than texture rendering, with oversized loose-fitting silhouettes being essential for achieving the correct aesthetic, decorated with asymmetric non-functional elements with extreme intricacy: precisely drawn straps with individual adjustment holes, detailed buckles showing metallic highlights through brightness variation, ribbons with visible fabric weave patterns, decorative chains with every link defined, small printed patterns where each motif is completely drawn not simplified, tiny mascot designs with full facial features and clothing details, elaborate lace trim with every loop and connection visible, embroidered sections showing individual thread directions, multiple button types each with unique design, decorative stitching patterns following realistic sewing logic, limiting accessories to exactly 2-3 carefully chosen focal points such as small hair ornaments in coordinated pastels, a simple bag or pouch with subtle decorations, and maximum one small keychain or charm attachment, rendering the face with eyes that occupy exactly one quarter of the face height with detailed gradient irises blending 3 carefully selected pastel colors, individually drawn eyelashes with natural variation, maintaining the essential sleepy half-closed drowsy expression with a slightly vacant melancholic gaze that defines the style's emotional quality, using only a tiny dot or subtle shadow for the nose and minimal to completely absent mouth to maintain the minimalist facial features, all line art must be rendered at MAXIMUM 1 pixel thickness only with absolutely no exceptions, ultra-thin delicate lines throughout entire image, thinner than pencil sketch lines, comparable to finest technical pen 0.03mm drawings, every line must be hairline thin including main outlines, every single decorative element fully realized with precision linework including individual lace patterns, detailed embroidery stitches, every button and buttonhole clearly defined, all fabric seams visible, intricate fold lines showing fabric structure, individual hair strands drawn separately with varying flow, delicate eyelash separation, fine jewelry chain links if present, tiny pattern details fully rendered not suggested, achieving supreme technical precision comparable to professional manga illustration with meticulous attention to smallest details, lines tinted to match adjacent colors rather than using black, employing dark blue-gray #4A5568 for main structural outlines only, with smooth antialiased curves throughout maintaining razor-sharp clarity, absolutely no line simplification or shorthand allowed, every ruffle edge individually drawn, every pleat carefully delineated, every decorative stitch shown, achieving a perfectly clean vector illustration quality with supreme intricacy and craftsmanship, comparable to professional Adobe Illustrator artwork with maximum detail density, where every millimeter of the illustration contains carefully considered details, intricate patterns within patterns, subtle design elements that reward close inspection, maintaining technical excellence of commercial game art and high-end character design standards, zero texture or noise but maximum detail complexity, sharp yet soft edges with perfect anti-aliasing, ensuring every decorative element from smallest button to tiniest embroidered flower is fully realized with complete internal detail not just suggested shapes, consistent professional production quality rejecting any amateur simplification, where every button, seam, fold, and decorative element is fully realized, individual hair strands are clearly defined, and the overall composition maintains perfect centering with generous margins around the character, showing the complete figure including footwear in perfectly upright vertical stance suitable for game sprite use, with absolutely no body tilting or leaning, head held straight without tilting left or right, shoulders perfectly level and horizontal, spine completely vertical, both feet planted firmly on same horizontal plane, maintaining symmetrical balance for clean game asset extraction, only the weight distribution can favor one leg while keeping overall posture perfectly vertical, ensuring the character can be cleanly extracted as game sprite without rotation correction, in a natural relaxed pose that maintains perfect vertical alignment rather than dynamic angled poses, creating an illustration that captures the exact aesthetic of modern Japanese character designs with their characteristic combination of cute styling, melancholic undertones, and sophisticated color harmony, maintaining the delicate balance between simplicity and detail that defines this particular art style."""
    
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

【重要】背景は均一なクロマキーグリーン (pure chroma key green background, RGB(0,255,0), #00FF00)。
キャラクターの輪郭線は背景から完全に独立し、グリーンのにじみや反射は一切なし。
Clean, sharp edge separation between character and green screen. No green color spill, fringing or halo around character.
Bright, well-lit character with high-key lighting to prevent dark/underexposed results.
Ensure character is bright and clearly visible with good contrast against green background.
質感テクスチャや落ち影は一切入れない。全身が頭からつま先までフレーム内に完全に収まること。

【色調（数値を使わない指定）】
overall color grading: bright pale tones, light grayish tones, soft muted pastel tones.
airy and bright atmosphere, emotional pastel look with good visibility.
no vivid or highly saturated colors, but maintain sufficient brightness.
medium-contrast tonal range for clear visibility, avoid crushed blacks and maintain bright whites.
Ensure overall bright exposure (high-key lighting) to prevent dark or muddy results.

【線（輪郭）】
outline color: clear, desaturated cool gray; not pure black but visible against green.
outer contour lines: bold and clean to create sharp silhouette against green background.
inner facial/detail lines: finer and lighter gray.
consistent, clean, sharp lines with no fuzzy edges; no sketchy strokes or messy hatching.
Ensure crisp, well-defined edges for clean chromakey extraction.

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
背景: 完全に均一な純粋グリーンスクリーン (RGB: 0, 255, 0 / #00FF00)。
輪郭線とグリーン背景の境界を明確に分離。エッジにグリーンのにじみなし。
no texture, no vignette, no gradient, no floor shadow, no green spill on character edges.

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

def generate_emo_with_vertex(character: EmoCharacter) -> List[bytes]:
    """エモ画像を生成（final_anime_prompt_v6.mdベース）"""
    if not credentials:
        raise HTTPException(status_code=500, detail="Credentials not configured")
    
    try:
        if credentials and hasattr(credentials, 'refresh'):
            credentials.refresh(Request())

        # エモ用のネガティブプロンプト（黒背景用）
        negative_prompt = "low quality, blurry, dark, underexposed, watermark, text, signature, multiple people, gray background, white background, gradient background, textured background"

        expressions = [
            ("smile", "gentle smile with slightly raised mouth corners"),
            ("neutral", "calm neutral expression"),
            ("surprised", "wide eyes with slightly open mouth"),
            ("troubled", "worried expression with furrowed brows"),
        ]

        base_prompt = create_emo_prompt(character)
        logger.info(f"Generated emo prompt (len={len(base_prompt)}) for character {character.character_id}")

        images: List[bytes] = []

        # 1枚目: テキストから生成
        first_name, first_desc = expressions[0]
        first_prompt = f"{base_prompt}\nExpression: {first_desc}"
        logger.info(f"Creating base emo image for expression: {first_name}")
        base_image = request_gemini_image(
            first_prompt,
            character.seed,
            negative_prompt=negative_prompt,
        )
        images.append(base_image)

        # 残り3枚: 並列処理で参照画像を使って表情のみ変更
        def generate_expression(expression_data):
            expression_name, expression_desc = expression_data
            logger.info(f"Starting parallel generation for emo expression: {expression_name}")
            edit_prompt = f"{base_prompt}\nEdit the provided image to change ONLY the facial expression to: {expression_desc}\nKeep everything else EXACTLY the same."
            try:
                result = request_gemini_image(
                    edit_prompt,
                    character.seed,
                    base_image=base_image,
                    negative_prompt=negative_prompt,
                )
                logger.info(f"Successfully generated emo expression: {expression_name}")
                return result
            except Exception as edit_error:
                logger.warning(
                    "Gemini edit failed for emo %s, fallback to fresh generation: %s",
                    expression_name,
                    edit_error,
                )
                fallback_prompt = f"{base_prompt}\nExpression: {expression_desc}"
                return request_gemini_image(
                    fallback_prompt,
                    character.seed,
                    negative_prompt=negative_prompt,
                )
        
        # ThreadPoolExecutorで並列実行
        logger.info("Starting parallel generation for 3 emo expression variations")
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_expression = {
                executor.submit(generate_expression, exp_data): idx 
                for idx, exp_data in enumerate(expressions[1:], start=1)
            }
            
            results = {}
            
            for future in as_completed(future_to_expression):
                idx = future_to_expression[future]
                try:
                    result = future.result(timeout=120)
                    results[idx] = result
                    logger.info(f"Emo expression {idx} generated successfully")
                except Exception as e:
                    logger.error(f"Emo expression {idx} generation failed: {e}")
                    raise HTTPException(status_code=500, detail=f"Failed to generate emo expression {idx}: {str(e)}")
            
            for idx in sorted(results.keys()):
                images.append(results[idx])
        
        logger.info(f"All {len(images)} emo images generated successfully")
        return images

    except Exception as e:
        logger.error(f"Emo image generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Emo image generation failed: {str(e)}")

def create_fantasy_prompt(character: FantasyCharacter) -> str:
    """ファンタジーキャラクター用のプロンプトを作成"""
    
    # 頭身の設定
    height_mapping = {
        "small": "youthful/petite proportions, 5-5.5 heads tall with youthful proportions, shorter height but normal realistic anatomy, NOT chibi or deformed style",
        "medium": "balanced proportions, exactly 6 heads tall, measure head size and make body exactly 5 more head lengths",
        "tall": "tall/elegant proportions, 7-8 heads tall with small head, long legs, elongated limbs for elegant mature style"
    }
    
    height_desc = height_mapping.get(character.height, height_mapping["medium"])
    
    prompt = f"""A high-quality fantasy character illustration in the style of premium Japanese mobile games, featuring a beautiful anime-style character with {character.hair_length} {character.hair_color} hair in {character.hair_style} style, wearing {character.outfit}. The character has {character.eye_shape} eyes in {character.eye_color} color, showing {character.expression} that captures their personality.

The character is shown in full body standing pose against a pure black background (#000000), displaying the entire outfit from head to toe. The character should have {height_desc}.

IMPORTANT: Even for youthful/petite option, maintain realistic human anatomy and proportions. This represents a younger or shorter character, NOT a stylized or deformed character. Keep facial features and body structure anatomically correct.

Use soft, muted color palette with low saturation around 40-60%. Apply pastel-like tones and gentle color gradations. Avoid harsh, vibrant colors - instead use subtle, desaturated hues with a dreamy, ethereal quality. Colors should have a milky, translucent feeling with plenty of white mixed in. Think watercolor-like softness rather than bold digital colors.

The artistic style should embody the sophisticated digital painting techniques seen in games like Granblue Fantasy or Fate/Grand Order, with extremely detailed linework using thin, delicate lines that vary in weight to create depth and flow. The line art should be colored rather than pure black, using darker tones of the local colors for each area.

The background must be completely black (#000000) to make the character stand out as a game asset or character portrait. No environmental elements, only the character against the black void.

For the coloring technique, employ a refined cel-shading approach with two distinct shadow layers. Shadows should be very subtle - first shadow only 8-10% darker than base color, second shadow 15-20% darker. Use warm gray or beige tones for shadows instead of pure darker colors. Blend shadows softly with gradient transitions.

Apply an overall atmospheric haze effect - as if viewing through soft focus or morning mist. Colors should blend into each other gently at the edges. Use opacity layers around 70-80% to create translucent, layered color effects.

The character's face should feature the distinctive anime style with large, expressive eyes that take up about 25-30% of the face area. Eye colors should be desaturated and soft - even bright colors like blue or green should appear gentle and muted.

Hair colors should be soft and muted - even vibrant colors like pink or blue should appear dusty and gentle, as if faded by sunlight. All clothing colors should be desaturated and soft - whites should be off-white or cream, blacks should be charcoal gray, bright colors should be dusty and muted.

Show the full body including legs and feet, with appropriate footwear that matches the outfit style.

Minimal to no magical effects or special elements. Focus solely on the character design itself without surrounding energy effects, auras, or magical circles.

Add a subtle rim light or outline glow around the character to ensure they pop from the black background, using soft pastel tones rather than bright neon colors.

Final color treatment: Apply a subtle color filter over the entire image to unify the palette - a very light overlay of cream, lavender, or pale blue to create cohesion. Reduce overall contrast slightly to maintain the soft, dreamy aesthetic."""

    return prompt

def generate_fantasy_with_vertex(character: FantasyCharacter) -> List[bytes]:
    """ファンタジーキャラクターの4つの表情バリエーションを生成"""
    if not credentials:
        logger.error("Credentials are None - not configured at all")
        raise HTTPException(status_code=500, detail="Credentials not configured")

    try:
        expressions = [
            ("neutral", f"{character.expression} - base expression showing character's default mood"),
            ("happy", f"happy and cheerful version of {character.expression}"),
            ("serious", f"serious and focused version of {character.expression}"),
            ("special", f"unique special expression variation of {character.expression}")
        ]

        negative_prompt = """low quality, pixelated, blurry, distorted anatomy, bad proportions,
        bright neon colors, oversaturated colors, harsh vivid colors, pure black shadows,
        environmental elements, background objects, multiple characters, chibi style,
        deformed features, floating particles, magical auras, energy effects"""

        base_prompt = create_fantasy_prompt(character)
        logger.info(f"Generated fantasy prompt (len={len(base_prompt)}) for character {character.character_id}")

        images: List[bytes] = []

        # 1枚目: テキストから生成
        first_name, first_desc = expressions[0]
        first_prompt = f"{base_prompt}\nExpression: {first_desc}"
        logger.info(f"Creating base fantasy image for expression: {first_name}")
        base_image = request_gemini_image(
            first_prompt,
            character.seed,
            negative_prompt=negative_prompt,
        )
        images.append(base_image)

        # 残り3枚: 並列処理で参照画像を使って表情のみ変更
        def generate_expression(expression_data):
            expression_name, expression_desc = expression_data
            logger.info(f"Starting parallel generation for fantasy expression: {expression_name}")
            edit_prompt = f"{base_prompt}\nEdit the provided image to change ONLY the facial expression to: {expression_desc}\nKeep everything else EXACTLY the same."
            try:
                result = request_gemini_image(
                    edit_prompt,
                    character.seed,
                    base_image=base_image,
                    negative_prompt=negative_prompt,
                )
                logger.info(f"Successfully generated fantasy expression: {expression_name}")
                return result
            except Exception as edit_error:
                logger.warning(
                    "Gemini edit failed for fantasy %s, fallback to fresh generation: %s",
                    expression_name,
                    edit_error,
                )
                fallback_prompt = f"{base_prompt}\nExpression: {expression_desc}"
                return request_gemini_image(
                    fallback_prompt,
                    character.seed,
                    negative_prompt=negative_prompt,
                )
        
        # ThreadPoolExecutorで並列実行
        logger.info("Starting parallel generation for 3 fantasy expression variations")
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_expression = {
                executor.submit(generate_expression, exp_data): idx 
                for idx, exp_data in enumerate(expressions[1:], start=1)
            }
            
            results = {}
            
            for future in as_completed(future_to_expression):
                idx = future_to_expression[future]
                try:
                    result = future.result(timeout=120)
                    results[idx] = result
                    logger.info(f"Fantasy expression {idx} generated successfully")
                except Exception as e:
                    logger.error(f"Failed to generate fantasy expression {idx}: {e}")
                    raise
            
            # 順番通りに追加
            for i in range(1, 4):
                if i in results:
                    images.append(results[i])
                    
        logger.info(f"Generated {len(images)} fantasy images successfully")
        return images

    except Exception as e:
        logger.error(f"Fantasy image generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fantasy image generation failed: {str(e)}")

@app.post("/api/generate/simple")
async def generate_images_simple(request: SimpleGenerateRequest):
    """簡略化されたキャラクター画像を生成するエンドポイント"""
    try:
        logger.info("========== /api/generate/simple endpoint called ==========")
        logger.info(f"Request data: {request.json()}")
        
        # 認証情報の確認
        logger.info(f"Checking credentials: {bool(credentials)}")
        logger.info(f"Credentials type: {type(credentials).__name__ if credentials else 'None'}")
        
        if not credentials:
            logger.error("Credentials are not configured at endpoint")
            raise HTTPException(
                status_code=500,
                detail="Authentication is not configured properly."
            )
        
        logger.info(f"PROJECT_ID: {PROJECT_ID}")
        logger.info(f"LOCATION: {LOCATION}")
        logger.info(f"MODEL_ID: {MODEL_ID}")
        
        # モードに応じた入力データのバリデーション
        if request.mode == "emo":
            if not request.emo_character:
                logger.error("Emo mode requires emo_character field")
                raise HTTPException(
                    status_code=422,
                    detail="emo_character is required for emo mode"
                )
            logger.info(f"Generating emo images for character: {request.emo_character.character_id}")
            
            # エモモード用の画像生成
            try:
                logger.info("Generating 4 emo expression variations")
                images = generate_emo_with_vertex(request.emo_character)
                logger.info(f"Successfully generated {len(images)} emo images")
                # エモモードは背景除去不要（黒背景のまま使用）
                processed_images = images
                skip_background_removal = True
            except Exception as e:
                logger.error(f"Failed to generate emo images: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to generate emo images: {str(e)}"
                )
        elif request.mode == "fantasy":
            if not request.fantasy_character:
                logger.error("Fantasy mode requires fantasy_character field")
                raise HTTPException(
                    status_code=422,
                    detail="fantasy_character is required for fantasy mode"
                )
            logger.info(f"Generating fantasy images for character: {request.fantasy_character.character_id}")
            
            # ファンタジーモード用の画像生成
            try:
                logger.info("Generating 4 fantasy expression variations")
                images = generate_fantasy_with_vertex(request.fantasy_character)
                logger.info(f"Successfully generated {len(images)} fantasy images")
                # ファンタジーモードは背景除去不要（黒背景のまま使用）
                processed_images = images
                skip_background_removal = True
            except Exception as e:
                logger.error(f"Failed to generate fantasy images: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to generate fantasy images: {str(e)}"
                )
        else:
            # 通常モード
            if not request.character:
                logger.error("Normal mode requires character field")
                raise HTTPException(
                    status_code=422,
                    detail="character is required for normal mode"
                )
            logger.info(f"Generating images for character: {request.character.character_id}")
            
            # 4つの表情バリエーションを順次生成（簡略化版）
            try:
                logger.info("Generating 4 expression variations with simplified data")
                
                # 簡略化された形式用の画像生成関数を呼び出し
                images = generate_images_with_vertex_simple(request.character)
                logger.info(f"Successfully generated {len(images)} images")
                skip_background_removal = False
            except Exception as e:
                logger.error(f"Failed to generate images: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to generate images: {str(e)}"
                )
        
        # グリーンバック除去（通常モードのみ）
        if not skip_background_removal:
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
