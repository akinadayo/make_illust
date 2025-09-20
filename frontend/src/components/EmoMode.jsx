import { useState } from 'react'
import './EmoMode.css'

function EmoMode({ setGeneratedImages, isGenerating, setIsGenerating }) {
  const [height, setHeight] = useState('medium')
  const [hair, setHair] = useState('')
  const [eyes, setEyes] = useState('')
  const [outfit, setOutfit] = useState('')
  const [error, setError] = useState('')

  const generateEmoImages = async () => {
    if (!hair.trim() || !eyes.trim() || !outfit.trim()) {
      setError('すべての項目を入力してください')
      return
    }

    setIsGenerating(true)
    setError('')

    const emoCharacter = {
      character_id: `emo_${Date.now()}`,
      seed: Math.floor(Math.random() * 1000000),
      height: height,
      hair: hair,
      eyes: eyes,
      outfit: outfit
    }

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'https://standing-set-backend-812480532939.asia-northeast1.run.app'
      console.log('Calling API for emo mode:', apiUrl)
      
      const response = await fetch(`${apiUrl}/api/generate/simple`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mode: 'emo',
          emo_character: emoCharacter,
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
      console.error('Emo generation error:', err)
      setError(`生成に失敗しました: ${err.message}`)
    } finally {
      setIsGenerating(false)
    }
  }

  const reset = () => {
    setHair('')
    setEyes('')
    setOutfit('')
    setHeight('medium')
    setError('')
    setGeneratedImages([])
  }

  return (
    <div className="emo-mode">
      <div className="emo-container">
        <div className="emo-header">
          <h2>エモ作成モード</h2>
          <p>アニメスタイルのキャラクターを生成します</p>
        </div>

        <div className="emo-form">
          <div className="form-group">
            <label>身長</label>
            <div className="height-buttons">
              <button 
                className={`height-btn ${height === 'small' ? 'active' : ''}`}
                onClick={() => setHeight('small')}
              >
                小さい
              </button>
              <button 
                className={`height-btn ${height === 'medium' ? 'active' : ''}`}
                onClick={() => setHeight('medium')}
              >
                普通
              </button>
              <button 
                className={`height-btn ${height === 'tall' ? 'active' : ''}`}
                onClick={() => setHeight('tall')}
              >
                大きめ
              </button>
            </div>
          </div>

          <div className="form-group">
            <label>髪型と髪色</label>
            <input
              type="text"
              value={hair}
              onChange={(e) => setHair(e.target.value)}
              placeholder="例: 黒のロングストレート、金髪のツインテール"
              className="emo-input"
            />
          </div>

          <div className="form-group">
            <label>目の形と色</label>
            <input
              type="text"
              value={eyes}
              onChange={(e) => setEyes(e.target.value)}
              placeholder="例: 大きい青い目、細めの茶色の目"
              className="emo-input"
            />
          </div>

          <div className="form-group">
            <label>服装</label>
            <input
              type="text"
              value={outfit}
              onChange={(e) => setOutfit(e.target.value)}
              placeholder="例: メイド服、制服、カジュアルな私服"
              className="emo-input"
            />
          </div>

          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          {isGenerating && (
            <div className="generating-message">
              エモを生成中... しばらくお待ちください（最大2分）
            </div>
          )}

          <div className="action-buttons">
            <button 
              onClick={generateEmoImages} 
              className="generate-button"
              disabled={isGenerating}
            >
              {isGenerating ? '生成中...' : 'エモを生成'}
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

export default EmoMode