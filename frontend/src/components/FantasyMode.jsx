import { useState } from 'react'
import './FantasyMode.css'

function FantasyMode({ setGeneratedImages, isGenerating, setIsGenerating }) {
  const [height, setHeight] = useState('medium')
  const [hairLength, setHairLength] = useState('')
  const [hairColor, setHairColor] = useState('')
  const [hairStyle, setHairStyle] = useState('')
  const [outfit, setOutfit] = useState('')
  const [eyeShape, setEyeShape] = useState('')
  const [eyeColor, setEyeColor] = useState('')
  const [expression, setExpression] = useState('')
  const [error, setError] = useState('')

  const generateFantasyImages = async () => {
    if (!hairLength.trim() || !hairColor.trim() || !hairStyle.trim() || 
        !outfit.trim() || !eyeShape.trim() || !eyeColor.trim() || !expression.trim()) {
      setError('すべての項目を入力してください')
      return
    }

    setIsGenerating(true)
    setError('')

    const fantasyCharacter = {
      character_id: `fantasy_${Date.now()}`,
      seed: Math.floor(Math.random() * 1000000),
      height: height,
      hair_length: hairLength,
      hair_color: hairColor,
      hair_style: hairStyle,
      outfit: outfit,
      eye_shape: eyeShape,
      eye_color: eyeColor,
      expression: expression
    }

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'https://standing-set-backend-812480532939.asia-northeast1.run.app'
      console.log('Calling API for fantasy mode:', apiUrl)
      
      const response = await fetch(`${apiUrl}/api/generate/simple`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mode: 'fantasy',
          fantasy_character: fantasyCharacter,
          return_type: 'base64_list'
        })
      })

      if (!response.ok) {
        throw new Error(`エラー: ${response.status}`)
      }

      const data = await response.json()
      
      if (data.images && data.images.length > 0) {
        setGeneratedImages(data.images)
      } else {
        throw new Error('画像が生成されませんでした')
      }
    } catch (err) {
      console.error('Fantasy generation error:', err)
      setError(`生成に失敗しました: ${err.message}`)
    } finally {
      setIsGenerating(false)
    }
  }

  const reset = () => {
    setHairLength('')
    setHairColor('')
    setHairStyle('')
    setOutfit('')
    setEyeShape('')
    setEyeColor('')
    setExpression('')
    setHeight('medium')
    setError('')
    setGeneratedImages([])
  }

  return (
    <div className="fantasy-mode">
      <div className="fantasy-container">
        <div className="fantasy-header">
          <h2>ファンタジー作成モード</h2>
          <p>高品質なファンタジーキャラクターを生成します</p>
        </div>

        <div className="fantasy-form">
          <div className="form-group">
            <label>頭身</label>
            <div className="height-buttons">
              <button 
                className={`height-btn ${height === 'small' ? 'active' : ''}`}
                onClick={() => setHeight('small')}
              >
                小さめ (5-5.5頭身)
              </button>
              <button 
                className={`height-btn ${height === 'medium' ? 'active' : ''}`}
                onClick={() => setHeight('medium')}
              >
                普通 (6頭身)
              </button>
              <button 
                className={`height-btn ${height === 'tall' ? 'active' : ''}`}
                onClick={() => setHeight('tall')}
              >
                大きめ (7-8頭身)
              </button>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>髪の長さ</label>
              <input
                type="text"
                value={hairLength}
                onChange={(e) => setHairLength(e.target.value)}
                placeholder="例: long, short, medium"
                className="fantasy-input"
              />
            </div>

            <div className="form-group">
              <label>髪色</label>
              <input
                type="text"
                value={hairColor}
                onChange={(e) => setHairColor(e.target.value)}
                placeholder="例: silver, blonde, black"
                className="fantasy-input"
              />
            </div>
          </div>

          <div className="form-group">
            <label>髪型</label>
            <input
              type="text"
              value={hairStyle}
              onChange={(e) => setHairStyle(e.target.value)}
              placeholder="例: straight, wavy, twintails, ponytail"
              className="fantasy-input"
            />
          </div>

          <div className="form-group">
            <label>服装</label>
            <input
              type="text"
              value={outfit}
              onChange={(e) => setOutfit(e.target.value)}
              placeholder="例: knight armor, mage robe, elegant dress"
              className="fantasy-input"
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>瞳の形</label>
              <input
                type="text"
                value={eyeShape}
                onChange={(e) => setEyeShape(e.target.value)}
                placeholder="例: large, narrow, almond-shaped"
                className="fantasy-input"
              />
            </div>

            <div className="form-group">
              <label>瞳の色</label>
              <input
                type="text"
                value={eyeColor}
                onChange={(e) => setEyeColor(e.target.value)}
                placeholder="例: blue, red, heterochromia"
                className="fantasy-input"
              />
            </div>
          </div>

          <div className="form-group">
            <label>表情・性格</label>
            <input
              type="text"
              value={expression}
              onChange={(e) => setExpression(e.target.value)}
              placeholder="例: confident, mysterious, gentle, cheerful"
              className="fantasy-input"
            />
          </div>

          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          {isGenerating && (
            <div className="generating-message">
              ファンタジーキャラクターを生成中... しばらくお待ちください（最大2分）
            </div>
          )}

          <div className="action-buttons">
            <button 
              onClick={generateFantasyImages} 
              className="generate-button"
              disabled={isGenerating}
            >
              {isGenerating ? '生成中...' : 'キャラクターを生成'}
            </button>
            <button 
              onClick={reset} 
              className="reset-button"
              disabled={isGenerating}
            >
              リセット
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default FantasyMode