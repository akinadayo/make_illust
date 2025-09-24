import React, { useState, useEffect, useRef } from 'react';
import './ParallaxLanding.css';

function ParallaxLanding({ backgroundImage, onStart }) {
    const [mousePos, setMousePos] = useState({ x: 0.5, y: 0.5 });
    const [layers, setLayers] = useState(null);
    const containerRef = useRef(null);
    
    useEffect(() => {
        // マウス移動を追跡
        const handleMouseMove = (e) => {
            const x = e.clientX / window.innerWidth;
            const y = e.clientY / window.innerHeight;
            setMousePos({ x, y });
        };

        // スマホのジャイロセンサー対応（オプション）
        const handleDeviceOrientation = (e) => {
            if (e.gamma && e.beta) {
                const x = (e.gamma + 90) / 180; // -90〜90度を0〜1に正規化
                const y = (e.beta + 180) / 360; // -180〜180度を0〜1に正規化
                setMousePos({ x, y });
            }
        };
        
        window.addEventListener('mousemove', handleMouseMove);
        window.addEventListener('deviceorientation', handleDeviceOrientation);
        
        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('deviceorientation', handleDeviceOrientation);
        };
    }, []);

    useEffect(() => {
        // 深度推定APIを呼び出して被写体を検出
        fetchDepthLayers();
    }, [backgroundImage]);

    const fetchDepthLayers = async () => {
        try {
            const apiUrl = import.meta.env.VITE_API_URL || 'https://standing-set-backend-812480532939.asia-northeast1.run.app';
            
            // 画像をbase64に変換
            const response = await fetch(backgroundImage);
            const blob = await response.blob();
            
            const formData = new FormData();
            formData.append('image_file', blob);
            
            const depthResponse = await fetch(`${apiUrl}/api/depth-estimation?use_depth_anything=false`, {
                method: 'POST',
                body: formData
            });

            if (depthResponse.ok) {
                const data = await depthResponse.json();
                console.log('Depth layers:', data);
                processDepthData(data);
            }
        } catch (error) {
            console.error('Failed to fetch depth layers:', error);
            // デフォルトのレイヤー設定を使用
            setDefaultLayers();
        }
    };

    const processDepthData = (data) => {
        const depthLayers = data.depth_layers;
        const subjectDetection = depthLayers.subject_detection;
        
        if (subjectDetection && subjectDetection.has_person) {
            // 被写体が検出された場合
            setLayers({
                background: {
                    depth: 1.0, // 最も遠い
                    parallaxStrength: 30,
                    blur: 2
                },
                midground: {
                    depth: 0.5,
                    parallaxStrength: 15,
                    blur: 0.5
                },
                foreground: {
                    depth: 0, // 最も近い
                    parallaxStrength: 5,
                    blur: 0,
                    bounds: subjectDetection.person_bounds
                }
            });
        } else {
            setDefaultLayers();
        }
    };

    const setDefaultLayers = () => {
        // デフォルトのレイヤー設定
        setLayers({
            background: {
                depth: 1.0,
                parallaxStrength: 25,
                blur: 1.5
            },
            foreground: {
                depth: 0,
                parallaxStrength: 8,
                blur: 0
            }
        });
    };

    const getLayerTransform = (layer) => {
        if (!layer) return '';
        
        // マウス位置を-1〜1の範囲に正規化
        const offsetX = (mousePos.x - 0.5) * 2;
        const offsetY = (mousePos.y - 0.5) * 2;
        
        // 深度に基づいて動きをスケール
        const moveX = offsetX * layer.parallaxStrength;
        const moveY = offsetY * layer.parallaxStrength * 0.5; // Y軸は控えめに
        
        // 深度に基づいてスケールも調整（遠いものは小さく）
        const scale = 1 + (layer.depth * 0.1);
        
        return `translate(${moveX}px, ${moveY}px) scale(${scale})`;
    };

    return (
        <div className="parallax-container" ref={containerRef}>
            {/* 背景レイヤー（最も遠い） */}
            <div 
                className="parallax-layer background-layer"
                style={{
                    backgroundImage: `url(${backgroundImage})`,
                    transform: getLayerTransform(layers?.background),
                    filter: `blur(${layers?.background?.blur || 0}px)`
                }}
            />
            
            {/* 中景レイヤー（オプション） */}
            {layers?.midground && (
                <div 
                    className="parallax-layer midground-layer"
                    style={{
                        backgroundImage: `url(${backgroundImage})`,
                        transform: getLayerTransform(layers.midground),
                        filter: `blur(${layers.midground.blur || 0}px)`,
                        maskImage: 'linear-gradient(to bottom, transparent 0%, black 30%, black 70%, transparent 100%)'
                    }}
                />
            )}
            
            {/* 前景レイヤー（被写体） */}
            <div 
                className="parallax-layer foreground-layer"
                style={{
                    backgroundImage: `url(${backgroundImage})`,
                    transform: getLayerTransform(layers?.foreground),
                    filter: `blur(${layers?.foreground?.blur || 0}px)`
                }}
            >
                {/* 被写体のマスク（検出された場合） */}
                {layers?.foreground?.bounds && (
                    <div 
                        className="subject-mask"
                        style={{
                            left: `${layers.foreground.bounds.x}%`,
                            top: `${layers.foreground.bounds.y}%`,
                            width: `${layers.foreground.bounds.width}%`,
                            height: `${layers.foreground.bounds.height}%`
                        }}
                    />
                )}
            </div>
            
            {/* UI要素（最前面） */}
            <div className="parallax-content">
                <h1 className="parallax-title" onClick={onStart}>TAP TO START</h1>
                <div className="depth-indicator">
                    {layers && (
                        <div className="depth-info">
                            <span>Depth Layers Active</span>
                            <span className="mouse-pos">
                                Mouse: {(mousePos.x * 100).toFixed(0)}%, {(mousePos.y * 100).toFixed(0)}%
                            </span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default ParallaxLanding;