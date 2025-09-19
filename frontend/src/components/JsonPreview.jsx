import { useState } from 'react'
import './JsonPreview.css'

function JsonPreview({ characterData }) {
  const [isExpanded, setIsExpanded] = useState(true)

  return (
    <div className="json-preview">
      <div className="json-header">
        <h3>JSON プレビュー</h3>
        <button 
          onClick={() => setIsExpanded(!isExpanded)}
          className="toggle-button"
        >
          {isExpanded ? '折りたたむ' : '展開'}
        </button>
      </div>
      
      {isExpanded && (
        <pre className="json-content">
          {JSON.stringify(characterData, null, 2)}
        </pre>
      )}
    </div>
  )
}

export default JsonPreview