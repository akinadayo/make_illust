import React, { useEffect, useState, useRef } from 'react';
import './LandingPage.css';
import ParallaxLanding from './ParallaxLanding';

const LandingPage = ({ onStart }) => {
    const [isLoading, setIsLoading] = useState(true);
    const [depthConfig, setDepthConfig] = useState(null);
    const animationFrameRef = useRef();
    const startTimeRef = useRef(Date.now());
    
    // Use haikei2.png as background
    const backgroundImage = '/背景/haikei2.png';

    useEffect(() => {
        // Initialize and fetch depth information
        initializeDepthParallax();
        
        // Create particles
        const particleInterval = setInterval(createParticle, 2000);
        for (let i = 0; i < 3; i++) {
            setTimeout(createParticle, i * 800);
        }

        // Create sparkles
        const sparkleInterval = setInterval(addSparkleToContainer, 3000);

        // Cleanup
        return () => {
            clearInterval(particleInterval);
            clearInterval(sparkleInterval);
            if (animationFrameRef.current) {
                cancelAnimationFrame(animationFrameRef.current);
            }
        };
    }, []);

    const initializeDepthParallax = async () => {
        // Use default parallax (depth estimation removed)
        useDefaultParallax();
        setIsLoading(false);
    };

    const useDefaultParallax = () => {
        const defaultConfig = {
            parallax_config: {
                layers: [
                    {
                        id: 'background',
                        depth: 90,
                        animations: [
                            { type: 'translateX', amplitude: 27, frequency: 0.033, phase: 0 },
                            { type: 'scale', amplitude: 0.005, frequency: 0.016, phase: 0.5 }
                        ]
                    },
                    {
                        id: 'midground',
                        depth: 50,
                        animations: [
                            { type: 'translateX', amplitude: 15, frequency: 0.04, phase: 0 },
                            { type: 'translateY', amplitude: 10, frequency: 0.033, phase: 0.25 },
                            { type: 'scale', amplitude: 0.025, frequency: 0.02, phase: 0.5 }
                        ]
                    },
                    {
                        id: 'foreground',
                        depth: 10,
                        animations: [
                            { type: 'translateX', amplitude: 3, frequency: 0.05, phase: 0 },
                            { type: 'scale', amplitude: 0.045, frequency: 0.025, phase: 0.5 }
                        ]
                    }
                ]
            }
        };
        setDepthConfig(defaultConfig);
        startParallaxAnimation(defaultConfig.parallax_config);
    };

    const startParallaxAnimation = (config) => {
        // マウス追従型の視差効果に移行
        // ParallaxLandingコンポーネントで実装
        console.log('Mouse-based parallax enabled');
    };

    const createParticle = () => {
        const particle = document.createElement('div');
        particle.className = 'hex-particle';
        
        const size = Math.random() * 15 + 10;
        const startX = Math.random() * window.innerWidth;
        const drift = (Math.random() - 0.5) * 100;
        
        particle.style.width = size + 'px';
        particle.style.height = size + 'px';
        particle.style.left = startX + 'px';
        particle.style.bottom = '-20px';
        particle.style.setProperty('--drift', drift + 'px');
        
        document.body.appendChild(particle);
        setTimeout(() => particle.remove(), 10000);
    };

    const createSparkle = (x, y) => {
        const sparkle = document.createElement('div');
        sparkle.className = 'sparkle';
        sparkle.style.left = x + 'px';
        sparkle.style.top = y + 'px';
        document.body.appendChild(sparkle);
        setTimeout(() => sparkle.remove(), 2000);
    };

    const addSparkleToContainer = () => {
        const container = document.querySelector('.tap-start-container');
        if (container) {
            const rect = container.getBoundingClientRect();
            const x = rect.left + Math.random() * rect.width;
            const y = rect.top + Math.random() * rect.height;
            createSparkle(x, y);
        }
    };

    const handleStart = () => {
        // Create ripple effect
        for (let i = 0; i < 3; i++) {
            setTimeout(() => {
                const ripple = document.createElement('div');
                ripple.className = 'ripple';
                ripple.style.left = '50%';
                ripple.style.top = '50%';
                ripple.style.width = '100px';
                ripple.style.height = '100px';
                ripple.style.marginLeft = '-50px';
                ripple.style.marginTop = '-50px';
                document.body.appendChild(ripple);
                setTimeout(() => ripple.remove(), 800);
            }, i * 100);
        }

        // Fade out and navigate
        const landingPage = document.querySelector('.landing-page');
        if (landingPage) {
            landingPage.style.transition = 'opacity 1s ease-out, filter 1s ease-out';
            landingPage.style.opacity = '0';
            landingPage.style.filter = 'blur(10px)';
        }

        setTimeout(() => {
            if (animationFrameRef.current) {
                cancelAnimationFrame(animationFrameRef.current);
            }
            onStart();
        }, 1000);
    };

    const renderDepthLayers = () => {
        if (!depthConfig) {
            // Default static layers while loading
            return (
                <>
                    <div 
                        id="layer-background"
                        className="bg-image bg-layer-depth active"
                        style={{
                            backgroundImage: `url('${backgroundImage}')`,
                            filter: 'blur(3px) brightness(0.8) saturate(1.2)',
                            transform: 'scale(1.3)',
                            zIndex: 1
                        }}
                    ></div>
                    <div 
                        id="layer-midground"
                        className="bg-image bg-layer-depth active"
                        style={{
                            backgroundImage: `url('${backgroundImage}')`,
                            filter: 'blur(1px) brightness(0.95)',
                            transform: 'scale(1.1)',
                            opacity: '0.8',
                            mixBlendMode: 'screen',
                            zIndex: 2
                        }}
                    ></div>
                    <div 
                        id="layer-foreground"
                        className="bg-layer-depth-front"
                        style={{
                            position: 'absolute',
                            bottom: '0',
                            left: '-5%',
                            width: '110%',
                            height: '50%',
                            backgroundImage: `url('${backgroundImage}')`,
                            backgroundPosition: 'center bottom',
                            backgroundSize: 'cover',
                            maskImage: `linear-gradient(to bottom, transparent 0%, rgba(0,0,0,0.5) 30%, black 60%)`,
                            WebkitMaskImage: `linear-gradient(to bottom, transparent 0%, rgba(0,0,0,0.5) 30%, black 60%)`,
                            filter: 'drop-shadow(0 -20px 30px rgba(0,0,0,0.2))',
                            zIndex: 3
                        }}
                    ></div>
                </>
            );
        }

        // Render depth-based layers - only show the main background image once
        const layers = depthConfig.depth_layers?.layers || [];
        
        // Only render the background image on the first (background) layer
        return layers.map((layer, index) => {
            const isBackground = index === 0;
            const isLast = index === layers.length - 1;
            
            if (!isBackground) {
                // Don't render additional layers - prevents duplicate images
                return null;
            }
            
            return (
                <div
                    key={layer.name}
                    id={`layer-${layer.name}`}
                    className="bg-image bg-layer-depth active"
                    style={{
                        backgroundImage: `url('${backgroundImage}')`,
                        filter: `blur(0px)`,
                        opacity: 1,
                        transform: 'scale(1)',
                        zIndex: 1,
                        willChange: 'transform'
                    }}
                />
            );
        });
    };

    // 新しいParallaxLandingコンポーネントを使用
    const useNewParallax = true;
    
    if (useNewParallax) {
        return <ParallaxLanding backgroundImage={backgroundImage} onStart={onStart} />;
    }
    
    // 旧実装（フォールバック用）
    return (
        <div className="landing-page">
            {/* Background layers */}
            <div className="bg-fallback"></div>
            <div className="bg-container" id="bgContainer">
                {renderDepthLayers()}
            </div>
            <div className="bg-overlay"></div>
            
            {/* Main content */}
            <div className="main-container">
                <div className="title-section">
                    <div className="title-glow"></div>
                    <h1 className="game-title">星灯のアルカディア</h1>
                    <p className="subtitle">～孤島に咲く二つの未来～</p>
                </div>
                
                <div className="tap-start-container" onClick={handleStart}>
                    <div className="tap-text">Tap to Start</div>
                </div>
            </div>

            {/* Loading indicator */}
            {isLoading && (
                <div className="depth-loading">
                    <div className="loading-text">深度解析中...</div>
                </div>
            )}
        </div>
    );
};

export default LandingPage;