import { useState } from 'react'
import './ChatInterview.css'

const questions = [
  {
    id: 'q1',
    question: 'どんなキャラクターを作りたいですか？年齢感を教えてください',
    hint: '例：高校生くらい、20代前半、小学生など',
    fields: ['age_appearance'],
    section: 'basic'
  },
  {
    id: 'q2',
    question: '身長と体型はどんな感じですか？',
    hint: '例：160cm、華奢 / 170cm、がっちり',
    fields: ['height_cm', 'build'],
    section: 'basic'
  },
  {
    id: 'q3',
    question: '髪の色と長さを教えてください',
    hint: '例：黒髪ロング、茶髪ショート、金髪セミロング',
    fields: ['color', 'length'],
    section: 'hair'
  },
  {
    id: 'q4',
    question: '髪型の特徴はありますか？',
    hint: '例：ツインテール、ポニーテール、ぱっつん前髪、ウェーブ',
    fields: ['bangs', 'style', 'accessories'],
    section: 'hair'
  },
  {
    id: 'q5',
    question: '目の色と形を教えてください',
    hint: '例：青い大きな目、茶色のつり目、緑のたれ目',
    fields: ['eyes_color', 'eyes_shape'],
    section: 'face'
  },
  {
    id: 'q6',
    question: 'どんな服装にしますか？',
    hint: '例：制服、カジュアル、和服、ファンタジー衣装',
    fields: ['style', 'top', 'bottom', 'shoes'],
    section: 'outfit'
  },
  {
    id: 'q7',
    question: 'キャラクターの性格を3つの言葉で表すと？',
    hint: '例：元気、やさしい、ドジっ子',
    fields: ['keywords'],
    section: 'persona'
  },
  {
    id: 'q8',
    question: 'このキャラクターの役割や職業は？',
    hint: '例：学生、冒険者、アイドル、店員さん',
    fields: ['role'],
    section: 'persona'
  },
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