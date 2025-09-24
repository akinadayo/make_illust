import React, { useEffect, useState, useRef } from 'react';
import './LandingPage.css';

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
        try {
            // Fetch depth estimation from backend
            const response = await fetch('http://localhost:8080/api/depth-estimation', {
                method: 'POST'
            });
            
            if (response.ok) {
                const data = await response.json();
                setDepthConfig(data);
                startParallaxAnimation(data.parallax_config);
            } else {
                // Use default parallax if API fails
                useDefaultParallax();
            }
        } catch (error) {
            console.error('Failed to fetch depth config:', error);
            useDefaultParallax();
        }
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
        const animate = () => {
            const elapsed = (Date.now() - startTimeRef.current) / 1000; // Elapsed time in seconds
            
            config.layers.forEach(layer => {
                const element = document.getElementById(`layer-${layer.id}`);
                if (!element) return;
                
                let transform = '';
                
                layer.animations.forEach(anim => {
                    const value = Math.sin((elapsed * anim.frequency * 2 * Math.PI) + anim.phase) * anim.amplitude;
                    
                    switch(anim.type) {
                        case 'translateX':
                            transform += `translateX(${value}px) `;
                            break;
                        case 'translateY':
                            transform += `translateY(${value}px) `;
                            break;
                        case 'scale':
                            transform += `scale(${1 + value}) `;
                            break;
                    }
                });
                
                element.style.transform = transform;
            });
            
            animationFrameRef.current = requestAnimationFrame(animate);
        };
        
        animate();
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

        // Render depth-based layers
        const layers = depthConfig.depth_layers?.layers || [];
        return layers.map((layer, index) => {
            const isLast = index === layers.length - 1;
            
            if (isLast) {
                // Special rendering for foreground layer
                return (
                    <div
                        key={layer.name}
                        id={`layer-${layer.name}`}
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
                            filter: `blur(${layer.blur || 0}px) drop-shadow(0 -20px 30px rgba(0,0,0,0.2))`,
                            opacity: layer.opacity,
                            zIndex: index + 1,
                            willChange: 'transform'
                        }}
                    />
                );
            }
            
            return (
                <div
                    key={layer.name}
                    id={`layer-${layer.name}`}
                    className="bg-image bg-layer-depth active"
                    style={{
                        backgroundImage: `url('${backgroundImage}')`,
                        filter: `blur(${layer.blur || 0}px) brightness(${0.8 + (index * 0.1)}) saturate(1.2)`,
                        opacity: layer.opacity,
                        transform: `scale(${layer.scale})`,
                        zIndex: index + 1,
                        mixBlendMode: index === 1 ? 'screen' : 'normal',
                        willChange: 'transform'
                    }}
                />
            );
        });
    };

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