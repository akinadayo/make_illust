"""
Depth Anything V2を使用した深度推定
Hugging Face Inference APIまたはローカルモデルを使用
"""
import base64
import io
import logging
import numpy as np
from PIL import Image
from typing import Dict, Any, Optional
import requests
import json

logger = logging.getLogger(__name__)

# Hugging Face Inference APIを使用する場合
HF_API_URL = "https://api-inference.huggingface.co/models/depth-anything/Depth-Anything-V2-Large-hf"

def estimate_depth_with_depth_anything(
    image_bytes: bytes,
    hf_token: Optional[str] = None,
    use_local: bool = False
) -> Dict[str, Any]:
    """
    Depth Anything V2を使用して深度推定を実行
    
    Args:
        image_bytes: 画像のバイトデータ
        hf_token: Hugging Face APIトークン（オプション）
        use_local: ローカルモデルを使用するか（要追加実装）
    
    Returns:
        深度マップと被写体検出情報
    """
    
    if use_local:
        # ローカルモデルを使用（transformersライブラリが必要）
        return estimate_depth_local(image_bytes)
    else:
        # Hugging Face Inference APIを使用
        return estimate_depth_hf_api(image_bytes, hf_token)


def estimate_depth_hf_api(image_bytes: bytes, hf_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Hugging Face Inference APIを使用した深度推定
    """
    try:
        headers = {}
        if hf_token:
            headers["Authorization"] = f"Bearer {hf_token}"
        
        # 画像をbase64エンコード
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # APIリクエスト
        response = requests.post(
            HF_API_URL,
            headers=headers,
            json={"inputs": image_base64},
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"HF API error: {response.status_code} - {response.text}")
            return get_default_depth_result()
        
        # レスポンスから深度マップを取得
        depth_map_base64 = response.json()
        
        # 深度マップを解析して被写体を検出
        return analyze_depth_map(depth_map_base64)
        
    except Exception as e:
        logger.error(f"Depth Anything API error: {e}")
        return get_default_depth_result()


def estimate_depth_local(image_bytes: bytes) -> Dict[str, Any]:
    """
    ローカルモデルを使用した深度推定（要実装）
    transformersライブラリを使用
    """
    try:
        from transformers import pipeline
        
        # パイプラインの初期化（初回のみ）
        depth_estimator = pipeline(
            task="depth-estimation",
            model="depth-anything/Depth-Anything-V2-Large-hf"
        )
        
        # PILイメージに変換
        image = Image.open(io.BytesIO(image_bytes))
        
        # 深度推定
        depth = depth_estimator(image)
        
        # 深度マップを解析
        return analyze_depth_array(depth["depth"])
        
    except ImportError:
        logger.error("transformers library not installed. Install with: pip install transformers torch")
        return get_default_depth_result()
    except Exception as e:
        logger.error(f"Local depth estimation error: {e}")
        return get_default_depth_result()


def analyze_depth_map(depth_map_base64: str) -> Dict[str, Any]:
    """
    深度マップを解析して被写体を検出
    """
    try:
        # Base64から画像に変換
        depth_bytes = base64.b64decode(depth_map_base64)
        depth_image = Image.open(io.BytesIO(depth_bytes)).convert('L')
        depth_array = np.array(depth_image)
        
        return analyze_depth_array(depth_array)
        
    except Exception as e:
        logger.error(f"Depth map analysis error: {e}")
        return get_default_depth_result()


def analyze_depth_array(depth_array: np.ndarray) -> Dict[str, Any]:
    """
    深度配列を解析して前景・中景・背景を識別
    """
    try:
        # 深度値の統計
        min_depth = np.min(depth_array)
        max_depth = np.max(depth_array)
        mean_depth = np.mean(depth_array)
        
        # 深度をパーセンタイルで分割
        percentiles = np.percentile(depth_array, [30, 70])
        
        # 前景、中景、背景のマスクを作成
        foreground_mask = depth_array < percentiles[0]
        midground_mask = (depth_array >= percentiles[0]) & (depth_array < percentiles[1])
        background_mask = depth_array >= percentiles[1]
        
        # 各領域の重心を計算（被写体位置の推定）
        def get_region_center(mask):
            coords = np.column_stack(np.where(mask))
            if len(coords) > 0:
                center_y = np.mean(coords[:, 0]) / depth_array.shape[0] * 100
                center_x = np.mean(coords[:, 1]) / depth_array.shape[1] * 100
                return {"x": center_x, "y": center_y}
            return {"x": 50, "y": 50}
        
        foreground_center = get_region_center(foreground_mask)
        
        # 前景領域の面積から人物の可能性を推定
        foreground_ratio = np.sum(foreground_mask) / depth_array.size
        has_person = 0.05 < foreground_ratio < 0.5  # 前景が画面の5-50%なら人物の可能性
        
        return {
            "subject_detection": {
                "has_person": has_person,
                "person_position": "foreground" if has_person else "unknown",
                "person_description": "Detected subject in foreground based on depth map",
                "person_bounds": {
                    "x": foreground_center["x"] - 20,
                    "y": foreground_center["y"] - 30,
                    "width": 40,
                    "height": 60
                },
                "confidence": foreground_ratio
            },
            "layers": [
                {
                    "name": "background",
                    "depth": 85,
                    "content": "Far background elements",
                    "parallax_strength": "strong",
                    "movement": "horizontal",
                    "scale": 1.3,
                    "blur": 2.5,
                    "opacity": 0.85,
                    "animation_speed": 35
                },
                {
                    "name": "midground",
                    "depth": 50,
                    "content": "Middle distance elements",
                    "parallax_strength": "medium",
                    "movement": "both",
                    "scale": 1.15,
                    "blur": 1,
                    "opacity": 0.92,
                    "animation_speed": 28
                },
                {
                    "name": "foreground",
                    "depth": 15,
                    "content": f"{'Person/subject detected' if has_person else 'Foreground elements'}",
                    "parallax_strength": "weak",
                    "movement": "horizontal",
                    "scale": 1.0,
                    "blur": 0,
                    "opacity": 1.0,
                    "animation_speed": 22
                }
            ],
            "depth_statistics": {
                "min": float(min_depth),
                "max": float(max_depth),
                "mean": float(mean_depth),
                "foreground_ratio": float(foreground_ratio)
            }
        }
        
    except Exception as e:
        logger.error(f"Depth array analysis error: {e}")
        return get_default_depth_result()


def get_default_depth_result() -> Dict[str, Any]:
    """
    デフォルトの深度推定結果
    """
    return {
        "subject_detection": {
            "has_person": False,
            "person_position": "unknown",
            "person_description": "No depth analysis available",
            "person_bounds": {"x": 50, "y": 50, "width": 30, "height": 40}
        },
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