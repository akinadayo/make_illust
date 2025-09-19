import { useState } from 'react'
import SimpleChatInterview from './components/SimpleChatInterview'
import ImagePreview from './components/ImagePreview'
import './App.css'

function App() {
  const [characterData, setCharacterData] = useState({
    character_id: `char_${Date.now()}`,
    seed: 123456789,
    basic: {
      age_appearance: '',
      height_cm: 160,
      build: ''
    },
    hair: {
      color: '',
      length: '',
      bangs: '',
      style: '',
      accessories: []
    },
    face: {
      eyes_color: '',
      eyes_shape: '',
      eyelashes: '標準',
      eyebrows: '標準',
      mouth: '標準',
      marks: []
    },
    outfit: {
      style: '',
      top: '',
      bottom: '',
      accessories: [],
      shoes: ''
    },
    persona: {
      keywords: [],
      role: ''
    },
    framing: {
      shot: '全身',
      camera: '正面、俯瞰なし、中心に全身が収まる、左右の余白を確保',
      pose: '直立、両腕は体側、自然体、足元まで映る'
    },
    constraints: {
      background: '白',
      forbid: ['背景小物', '武器', '他キャラ', '文字', '透かし', 'テクスチャ', '床影', '強コントラスト']
    }
  })

  const [generatedImages, setGeneratedImages] = useState([])
  const [isGenerating, setIsGenerating] = useState(false)

  return (
    <div className="app">
      <header className="app-header">
        <h1>キャラクター立ち絵ジェネレーター</h1>
        <p>チャットで質問に答えて、5つの表情を一括生成</p>
      </header>

      <div className="app-content">
        <SimpleChatInterview 
          characterData={characterData}
          setCharacterData={setCharacterData}
          setGeneratedImages={setGeneratedImages}
          isGenerating={isGenerating}
          setIsGenerating={setIsGenerating}
        />

        {generatedImages.length > 0 && (
          <ImagePreview images={generatedImages} />
        )}
      </div>
    </div>
  )
}

export default App
