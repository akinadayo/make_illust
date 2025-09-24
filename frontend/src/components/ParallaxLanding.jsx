import React, { useState, useEffect, useRef } from 'react';
import './ParallaxLanding.css';

function ParallaxLanding({ backgroundImage, onStart }) {
    const [animationTime, setAnimationTime] = useState(0);
    const [layers, setLayers] = useState(null);
    const containerRef = useRef(null);
    const animationRef = useRef(null);
    
    useEffect(() => {
        // 自動アニメーション
        const animate = () => {
            setAnimationTime(prev => prev + 0.01); // ゆっくりと時間を進める
            animationRef.current = requestAnimationFrame(animate);
        };
        
        animationRef.current = requestAnimationFrame(animate);
        
        return () => {
            if (animationRef.current) {
                cancelAnimationFrame(animationRef.current);
            }
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

    const getLayerTransform = (layer, layerIndex = 0) => {
        if (!layer) return '';
        
        // 各レイヤーごとに異なる動きのパターンを生成
        // ゆっくりとした円運動のような自然な動き
        const speed = layer.parallaxStrength * 0.02; // 速度を調整
        const phase = layerIndex * Math.PI * 0.5; // 各レイヤーで位相をずらす
        
        // 8の字を描くような複雑な動き
        const moveX = Math.sin(animationTime * speed + phase) * layer.parallaxStrength;
        const moveY = Math.sin(animationTime * speed * 0.7 + phase) * layer.parallaxStrength * 0.3;
        
        // 微妙なスケール変化も追加（呼吸するような効果）
        const scaleOscillation = Math.sin(animationTime * speed * 0.5) * 0.02;
        const scale = 1 + (layer.depth * 0.05) + scaleOscillation;
        
        return `translate(${moveX}px, ${moveY}px) scale(${scale})`;
    };

    return (
        <div className="parallax-container" ref={containerRef}>
            {/* 背景レイヤー（最も遠い） */}
            <div 
                className="parallax-layer background-layer"
                style={{
                    backgroundImage: `url(${backgroundImage})`,
                    transform: getLayerTransform(layers?.background, 0),
                    filter: `blur(${layers?.background?.blur || 0}px)`
                }}
            />
            
            {/* 中景レイヤー（オプション） */}
            {layers?.midground && (
                <div 
                    className="parallax-layer midground-layer"
                    style={{
                        backgroundImage: `url(${backgroundImage})`,
                        transform: getLayerTransform(layers.midground, 1),
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
                    transform: getLayerTransform(layers?.foreground, 2),
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
                <div className="app-title">
                    <h1 className="main-title">Standing-Set-5</h1>
                    <p className="subtitle">AI Character Generator</p>
                </div>
                <h2 className="parallax-title" data-text="TAP TO START" onClick={onStart}>TAP TO START</h2>
                <div className="depth-indicator">
                    {layers && (
                        <div className="depth-info">
                            <span>Parallax Active</span>
                            <span className="animation-time">
                                Time: {animationTime.toFixed(1)}s
                            </span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default ParallaxLanding;