import { useState } from 'react'
import './ChatInterview.css'

const questions = [
  {
    id: 'q1',
    question: 'Q1. 年齢感・身長・体格を教えてください',
    hint: '例：高校生くらい／160cm／華奢',
    fields: ['age_appearance', 'height_cm', 'build'],
    section: 'basic'
  },
  {
    id: 'q2',
    question: 'Q2. 髪について教えてください',
    hint: '色／長さ／前髪／スタイル／アクセサリー',
    fields: ['color', 'length', 'bangs', 'style', 'accessories'],
    section: 'hair'
  },
  {
    id: 'q3',
    question: 'Q3. 顔の特徴を教えてください',
    hint: '目の色／目の形／まつ毛／眉／口／ほくろなどの特徴',
    fields: ['eyes_color', 'eyes_shape', 'eyelashes', 'eyebrows', 'mouth', 'marks'],
    section: 'face'
  },
  {
    id: 'q4',
    question: 'Q4. 服装について教えてください',
    hint: '系統＋具体：上／下／小物／靴',
    fields: ['style', 'top', 'bottom', 'accessories', 'shoes'],
    section: 'outfit'
  },
  {
    id: 'q5',
    question: 'Q5. 性格3語＋役割を教えてください',
    hint: '例：おっとり・芯が強い・ドジ／神社で手伝う生徒',
    fields: ['keywords', 'role'],
    section: 'persona'
  },
  {
    id: 'q6',
    question: 'Q6. 構図について',
    hint: '全身・正面・直立でよろしいですか？',
    confirm: true,
    defaultAnswer: 'はい'
  },
  {
    id: 'confirm1',
    question: '確認A）背景は白、他キャラ・小物・文字・武器なしでよろしいですか？',
    confirm: true,
    defaultAnswer: 'はい'
  },
  {
    id: 'confirm2',
    question: '確認B）色はペール＆ライトグレイッシュ／輪郭は灰色ラインで統一してよろしいですか？',
    confirm: true,
    defaultAnswer: 'はい'
  }
]

function ChatInterview({ characterData, setCharacterData }) {
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [currentAnswer, setCurrentAnswer] = useState('')
  const [chatHistory, setChatHistory] = useState([])
  const [isComplete, setIsComplete] = useState(false)

  const currentQuestion = questions[currentQuestionIndex]

  const handleAnswerSubmit = () => {
    if (!currentAnswer.trim() && !currentQuestion.confirm) return

    // Add to chat history
    setChatHistory([...chatHistory, {
      question: currentQuestion.question,
      answer: currentAnswer || currentQuestion.defaultAnswer
    }])

    // Parse and update character data
    if (!currentQuestion.confirm) {
      const updatedData = { ...characterData }
      const section = updatedData[currentQuestion.section]
      
      if (currentQuestion.section === 'basic') {
        const parts = currentAnswer.split('／')
        if (parts[0]) section.age_appearance = parts[0].trim()
        if (parts[1]) {
          const height = parseInt(parts[1].replace(/[^0-9]/g, ''))
          if (height >= 120 && height <= 200) {
            section.height_cm = height
          }
        }
        if (parts[2]) section.build = parts[2].trim()
      } else if (currentQuestion.section === 'hair') {
        const parts = currentAnswer.split('／')
        if (parts[0]) section.color = parts[0].trim()
        if (parts[1]) section.length = parts[1].trim()
        if (parts[2]) section.bangs = parts[2].trim()
        if (parts[3]) section.style = parts[3].trim()
        if (parts[4]) {
          section.accessories = parts[4].split('、').map(a => a.trim()).filter(a => a)
        }
      } else if (currentQuestion.section === 'face') {
        const parts = currentAnswer.split('／')
        if (parts[0]) section.eyes_color = parts[0].trim()
        if (parts[1]) section.eyes_shape = parts[1].trim()
        if (parts[2]) section.eyelashes = parts[2].trim()
        if (parts[3]) section.eyebrows = parts[3].trim()
        if (parts[4]) section.mouth = parts[4].trim()
        if (parts[5]) {
          section.marks = parts[5].split('、').map(m => m.trim()).filter(m => m)
        }
      } else if (currentQuestion.section === 'outfit') {
        const parts = currentAnswer.split('／')
        if (parts[0]) section.style = parts[0].trim()
        if (parts[1]) section.top = parts[1].trim()
        if (parts[2]) section.bottom = parts[2].trim()
        if (parts[3]) {
          section.accessories = parts[3].split('、').map(a => a.trim()).filter(a => a)
        }
        if (parts[4]) section.shoes = parts[4].trim()
      } else if (currentQuestion.section === 'persona') {
        const parts = currentAnswer.split('／')
        if (parts[0]) {
          section.keywords = parts[0].split('・').map(k => k.trim()).filter(k => k)
        }
        if (parts[1]) section.role = parts[1].trim()
      }
      
      setCharacterData(updatedData)
    }

    // Move to next question or complete
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1)
      setCurrentAnswer('')
    } else {
      setIsComplete(true)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleAnswerSubmit()
    }
  }

  const handleReset = () => {
    setCurrentQuestionIndex(0)
    setCurrentAnswer('')
    setChatHistory([])
    setIsComplete(false)
  }

  return (
    <div className="chat-interview">
      <h2>キャラクター設定インタビュー</h2>
      
      <div className="chat-history">
        {chatHistory.map((item, index) => (
          <div key={index} className="chat-item">
            <div className="chat-question">{item.question}</div>
            <div className="chat-answer">→ {item.answer}</div>
          </div>
        ))}
      </div>

      {!isComplete ? (
        <div className="current-question">
          <div className="question-text">
            {currentQuestion.question}
          </div>
          {currentQuestion.hint && (
            <div className="question-hint">{currentQuestion.hint}</div>
          )}
          
          <div className="answer-input-container">
            {currentQuestion.confirm ? (
              <div className="confirm-buttons">
                <button 
                  onClick={() => {
                    setCurrentAnswer('はい')
                    handleAnswerSubmit()
                  }}
                  className="confirm-yes"
                >
                  はい
                </button>
                <button 
                  onClick={() => {
                    setCurrentAnswer('いいえ（カスタマイズ希望）')
                    handleAnswerSubmit()
                  }}
                  className="confirm-no"
                >
                  いいえ
                </button>
              </div>
            ) : (
              <>
                <textarea
                  value={currentAnswer}
                  onChange={(e) => setCurrentAnswer(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="回答を入力してください..."
                  rows={3}
                  className="answer-input"
                />
                <button 
                  onClick={handleAnswerSubmit}
                  className="submit-button"
                >
                  送信
                </button>
              </>
            )}
          </div>
        </div>
      ) : (
        <div className="interview-complete">
          <p>インタビュー完了！右側のJSONプレビューを確認して、生成ボタンをクリックしてください。</p>
          <button onClick={handleReset} className="reset-button">
            最初からやり直す
          </button>
        </div>
      )}
    </div>
  )
}

export default ChatInterview