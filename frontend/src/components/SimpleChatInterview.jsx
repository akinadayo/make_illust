import { useState } from 'react'
import './SimpleChatInterview.css'

const questions = [
  { id: 1, text: 'どんなキャラクターを作りたいですか？年齢感を教えてください', field: 'age' },
  { id: 2, text: '身長と体型はどんな感じ？', field: 'body' },
  { id: 3, text: '髪の色と長さは？', field: 'hair_basic' },
  { id: 4, text: '髪型の特徴は？（ツインテールなど）', field: 'hair_style' },
  { id: 5, text: '目の色と形は？', field: 'eyes' },
  { id: 6, text: 'どんな服装？', field: 'outfit' },
  { id: 7, text: '性格を3つの言葉で表すと？', field: 'personality' },
  { id: 8, text: 'このキャラの役割や職業は？', field: 'role' }
]

function SimpleChatInterview({ characterData, setCharacterData, setGeneratedImages, isGenerating, setIsGenerating }) {
  const [currentQuestion, setCurrentQuestion] = useState(0)
  const [answer, setAnswer] = useState('')
  const [answers, setAnswers] = useState({})
  const [isComplete, setIsComplete] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    if (!answer.trim()) return

    const newAnswers = { ...answers, [questions[currentQuestion].field]: answer }
    setAnswers(newAnswers)
    setAnswer('')

    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion(currentQuestion + 1)
    } else {
      setIsComplete(true)
      await generateImages(newAnswers)
    }
  }

  const generateImages = async (allAnswers) => {
    setIsGenerating(true)
    setError('')

    // 簡略化されたキャラクターデータを構築
    const simpleCharacter = {
      character_id: `char_${Date.now()}`,
      seed: Math.floor(Math.random() * 1000000),
      age: allAnswers.age || '20代',
      body_type: allAnswers.body || 'スレンダー',
      eyes: allAnswers.eyes || '大きな茶色の瞳',
      hair: `${allAnswers.hair_basic || '黒のロング'}、${allAnswers.hair_style || 'ストレート'}`,
      outfit: allAnswers.outfit || 'カジュアルな私服',
      accessories: '',  // 今回は空
      other_features: allAnswers.personality ? `性格: ${allAnswers.personality}` : ''
    }

    // 複雑な形式も保持（将来の互換性のため）
    setCharacterData(simpleCharacter)

    // APIコール
    try {
      // 本番環境では必ずhttpsのURLを使用
      const apiUrl = import.meta.env.VITE_API_URL || 'https://standing-set-backend-812480532939.asia-northeast1.run.app'
      console.log('Calling API:', apiUrl)
      
      const response = await fetch(`${apiUrl}/api/generate/simple`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          character: simpleCharacter,
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
      console.error('Generation error:', err)
      setError(`生成に失敗しました: ${err.message}`)
    } finally {
      setIsGenerating(false)
    }
  }

  const restart = () => {
    setCurrentQuestion(0)
    setAnswers({})
    setIsComplete(false)
    setAnswer('')
    setError('')
    setGeneratedImages([])
  }

  return (
    <div className="chat-interview">
      <div className="chat-container">
        <div className="chat-messages">
          {Object.keys(answers).map((field, idx) => (
            <div key={idx} className="message-pair">
              <div className="message bot">{questions[idx].text}</div>
              <div className="message user">{answers[field]}</div>
            </div>
          ))}
          
          {!isComplete && (
            <div className="message bot current">
              {questions[currentQuestion].text}
            </div>
          )}

          {isComplete && !isGenerating && !error && (
            <div className="message bot">
              すべての質問に答えていただきありがとうございます！画像を生成しました。
            </div>
          )}

          {isGenerating && (
            <div className="message bot">
              画像を生成中です... しばらくお待ちください（最大2分）
            </div>
          )}

          {error && (
            <div className="message error">
              {error}
              <button onClick={() => generateImages(answers)} className="retry-button">
                もう一度試す
              </button>
            </div>
          )}
        </div>

        {!isComplete && (
          <div className="input-area">
            <input
              type="text"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSubmit()}
              placeholder="回答を入力..."
              className="chat-input"
            />
            <button onClick={handleSubmit} className="send-button">
              送信
            </button>
          </div>
        )}

        {isComplete && (
          <button onClick={restart} className="restart-button">
            最初からやり直す
          </button>
        )}
      </div>
    </div>
  )
}

export default SimpleChatInterview