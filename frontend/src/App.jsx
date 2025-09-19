import { useState } from 'react'
import ChatInterview from './components/ChatInterview'
import JsonPreview from './components/JsonPreview'
import GenerateButton from './components/GenerateButton'
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

  const [isGenerating, setIsGenerating] = useState(false)
  const [generationMessage, setGenerationMessage] = useState('')

  return (
    <div className="app">
      <header className="app-header">
        <h1>立ち絵5表情・一括生成アプリ</h1>
        <p>チャットでキャラクター設定を入力して、5つの表情差分を一括生成</p>
      </header>

      <div className="app-content">
        <div className="left-panel">
          <ChatInterview 
            characterData={characterData}
            setCharacterData={setCharacterData}
          />
        </div>

        <div className="right-panel">
          <JsonPreview characterData={characterData} />
          
          <GenerateButton 
            characterData={characterData}
            isGenerating={isGenerating}
            setIsGenerating={setIsGenerating}
            setGenerationMessage={setGenerationMessage}
          />

          {generationMessage && (
            <div className="generation-message">
              {generationMessage}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
