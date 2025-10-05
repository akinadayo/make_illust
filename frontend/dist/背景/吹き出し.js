import React, { useState, useRef, useEffect } from 'react';

const CyberpunkSpeechBubble = () => {
  const [text, setText] = useState('メッセージを入力...');
  const [bubbleSize, setBubbleSize] = useState({ width: 250, height: 80 });
  const textRef = useRef(null);

  useEffect(() => {
    if (textRef.current) {
      const textElement = textRef.current;
      const bbox = textElement.getBBox();
      
      // パディングを追加してサイズを計算
      const padding = 40;
      const minWidth = 200;
      const minHeight = 60;
      
      const newWidth = Math.max(bbox.width + padding * 2, minWidth);
      const newHeight = Math.max(bbox.height + padding * 1.5, minHeight);
      
      setBubbleSize({ 
        width: newWidth, 
        height: newHeight 
      });
    }
  }, [text]);

  const handleTextChange = (e) => {
    setText(e.target.value || 'メッセージを入力...');
  };

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      gap: '30px',
      padding: '20px',
      background: 'linear-gradient(135deg, #1a1a2e 0%, #0a0a1a 100%)',
      minHeight: '100vh'
    }}>
      <h2 style={{ 
        color: '#00ffff', 
        textShadow: '0 0 20px #00ffff',
        fontFamily: 'Arial, sans-serif',
        letterSpacing: '2px'
      }}>
        CYBERPUNK SPEECH BUBBLE
      </h2>
      
      {/* SVG吹き出し */}
      <svg 
        width={bubbleSize.width + 100} 
        height={bubbleSize.height + 80} 
        viewBox={`0 0 ${bubbleSize.width + 100} ${bubbleSize.height + 80}`}
        style={{ filter: 'drop-shadow(0 0 20px rgba(0, 255, 255, 0.5))' }}
      >
        <defs>
          {/* グラデーション */}
          <linearGradient id="borderGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#00ffff" stopOpacity="1">
              <animate attributeName="stopColor" 
                values="#00ffff;#ff00ff;#00ffff" 
                dur="4s" 
                repeatCount="indefinite" />
            </stop>
            <stop offset="100%" stopColor="#ff00ff" stopOpacity="1">
              <animate attributeName="stopColor" 
                values="#ff00ff;#00ffff;#ff00ff" 
                dur="4s" 
                repeatCount="indefinite" />
            </stop>
          </linearGradient>
          
          {/* 背景パターン */}
          <pattern id="hexGrid" x="0" y="0" width="30" height="26" patternUnits="userSpaceOnUse">
            <polygon 
              points="15,1 27,7.5 27,18.5 15,25 3,18.5 3,7.5" 
              fill="none" 
              stroke="#00ffff" 
              strokeWidth="0.3" 
              opacity="0.2"
            />
          </pattern>
          
          {/* グロー効果 */}
          <filter id="glow">
            <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
          
          <filter id="textGlow">
            <feGaussianBlur stdDeviation="2" result="softBlur"/>
            <feMerge>
              <feMergeNode in="softBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        
        {/* メインの吹き出し */}
        <g transform="translate(20, 20)">
          {/* 吹き出し本体 */}
          <rect 
            x="0" 
            y="0" 
            width={bubbleSize.width} 
            height={bubbleSize.height}
            rx="15" 
            ry="15"
            fill="#0a0a1a"
            fillOpacity="0.9"
            stroke="url(#borderGradient)"
            strokeWidth="2"
            filter="url(#glow)"
          />
          
          {/* 六角形パターンオーバーレイ */}
          <rect 
            x="0" 
            y="0" 
            width={bubbleSize.width} 
            height={bubbleSize.height}
            rx="15" 
            ry="15"
            fill="url(#hexGrid)"
            opacity="0.5"
          />
          
          {/* 吹き出しの尾 */}
          <path 
            d={`M ${bubbleSize.width * 0.2} ${bubbleSize.height} 
                L ${bubbleSize.width * 0.15} ${bubbleSize.height + 25} 
                L ${bubbleSize.width * 0.3} ${bubbleSize.height}`}
            fill="#0a0a1a"
            fillOpacity="0.9"
            stroke="url(#borderGradient)"
            strokeWidth="2"
            filter="url(#glow)"
          />
          
          {/* コーナー装飾 */}
          <circle cx="10" cy="10" r="3" fill="#00ffff" opacity="0.8" filter="url(#glow)"/>
          <circle cx={bubbleSize.width - 10} cy="10" r="3" fill="#ff00ff" opacity="0.8" filter="url(#glow)"/>
          <circle cx="10" cy={bubbleSize.height - 10} r="3" fill="#ff00ff" opacity="0.8" filter="url(#glow)"/>
          <circle cx={bubbleSize.width - 10} cy={bubbleSize.height - 10} r="3" fill="#00ffff" opacity="0.8" filter="url(#glow)"/>
          
          {/* テキスト */}
          <text 
            ref={textRef}
            x={bubbleSize.width / 2} 
            y={bubbleSize.height / 2} 
            textAnchor="middle" 
            dominantBaseline="middle"
            fill="#00ffff"
            fontSize="18"
            fontFamily="'Courier New', monospace"
            filter="url(#textGlow)"
            style={{ userSelect: 'none' }}
          >
            {text.split('\n').map((line, i) => (
              <tspan key={i} x={bubbleSize.width / 2} dy={i === 0 ? 0 : 25}>
                {line}
              </tspan>
            ))}
          </text>
        </g>
        
        {/* アニメーション装飾 */}
        <circle r="2" fill="#00ffff" opacity="0.6">
          <animateMotion 
            path={`M 30 30 Q ${bubbleSize.width / 2} 10, ${bubbleSize.width} 30`}
            dur="5s" 
            repeatCount="indefinite"/>
          <animate attributeName="opacity" values="0.6;1;0.6" dur="1s" repeatCount="indefinite"/>
        </circle>
      </svg>
      
      {/* 入力フィールド */}
      <div style={{ 
        width: '100%', 
        maxWidth: '500px',
        padding: '20px',
        background: 'rgba(0, 255, 255, 0.05)',
        border: '1px solid #00ffff',
        borderRadius: '10px',
        boxShadow: '0 0 20px rgba(0, 255, 255, 0.2)'
      }}>
        <label style={{ 
          color: '#00ffff', 
          fontSize: '14px',
          fontFamily: 'Arial, sans-serif',
          display: 'block',
          marginBottom: '10px',
          textTransform: 'uppercase',
          letterSpacing: '1px'
        }}>
          テキスト入力
        </label>
        <textarea
          value={text === 'メッセージを入力...' ? '' : text}
          onChange={handleTextChange}
          placeholder="メッセージを入力..."
          style={{
            width: '100%',
            minHeight: '80px',
            padding: '10px',
            background: 'rgba(0, 0, 0, 0.5)',
            border: '1px solid #00ffff',
            borderRadius: '5px',
            color: '#00ffff',
            fontSize: '16px',
            fontFamily: "'Courier New', monospace",
            resize: 'vertical',
            outline: 'none',
            transition: 'all 0.3s ease'
          }}
          onFocus={(e) => {
            e.target.style.boxShadow = '0 0 10px #00ffff';
            if (text === 'メッセージを入力...') setText('');
          }}
          onBlur={(e) => {
            e.target.style.boxShadow = 'none';
            if (text === '') setText('メッセージを入力...');
          }}
        />
        <div style={{ 
          marginTop: '10px', 
          fontSize: '12px', 
          color: '#ff00ff',
          textAlign: 'right'
        }}>
          文字数: {text === 'メッセージを入力...' ? 0 : text.length}
        </div>
      </div>
      
      {/* 使用方法 */}
      <div style={{ 
        maxWidth: '500px',
        padding: '15px',
        background: 'rgba(255, 0, 255, 0.05)',
        border: '1px solid #ff00ff',
        borderRadius: '10px',
        color: '#ff00ff',
        fontSize: '14px',
        fontFamily: 'Arial, sans-serif'
      }}>
        <strong>特徴:</strong>
        <ul style={{ marginTop: '10px', paddingLeft: '20px' }}>
          <li>文字数に応じて自動リサイズ</li>
          <li>グラデーションアニメーション</li>
          <li>サイバーパンク風ネオン効果</li>
          <li>六角形グリッドパターン</li>
        </ul>
      </div>
    </div>
  );
};

export default CyberpunkSpeechBubble;