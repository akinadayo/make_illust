import { useState } from 'react'
import './GenerateButton.css'

function GenerateButton({ characterData, isGenerating, setIsGenerating, setGenerationMessage }) {
  const [downloadUrl, setDownloadUrl] = useState(null)

  const validateCharacterData = () => {
    const required = [
      characterData.basic.age_appearance,
      characterData.basic.build,
      characterData.hair.color,
      characterData.hair.length,
      characterData.face.eyes_color,
      characterData.outfit.style,
      characterData.outfit.top,
      characterData.outfit.bottom,
      characterData.persona.keywords.length > 0,
      characterData.persona.role
    ]
    
    return required.every(field => field)
  }

  const handleGenerate = async () => {
    if (!validateCharacterData()) {
      setGenerationMessage('必須項目をすべて入力してください')
      setTimeout(() => setGenerationMessage(''), 3000)
      return
    }

    setIsGenerating(true)
    setGenerationMessage('画像を生成中です... (最大5分かかる場合があります)')
    
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8080'
      
      const response = await fetch(`${apiUrl}/api/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          character: characterData,
          return_type: 'zip'
        })
      })

      if (!response.ok) {
        const error = await response.text()
        throw new Error(error || `HTTP error! status: ${response.status}`)
      }

      // Handle ZIP file download
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      setDownloadUrl(url)
      
      // Auto-download
      const a = document.createElement('a')
      a.href = url
      a.download = `standing_set_${characterData.character_id}.zip`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      
      setGenerationMessage('生成完了！ダウンロードが開始されました。')
      
    } catch (error) {
      console.error('Generation error:', error)
      setGenerationMessage(`エラーが発生しました: ${error.message}`)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleGenerateBase64 = async () => {
    if (!validateCharacterData()) {
      setGenerationMessage('必須項目をすべて入力してください')
      setTimeout(() => setGenerationMessage(''), 3000)
      return
    }

    setIsGenerating(true)
    setGenerationMessage('画像を生成中です... (最大5分かかる場合があります)')
    
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8080'
      
      const response = await fetch(`${apiUrl}/api/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          character: characterData,
          return_type: 'base64_list'
        })
      })

      if (!response.ok) {
        const error = await response.text()
        throw new Error(error || `HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      
      // Display images or handle them as needed
      if (data.images && data.images.length > 0) {
        setGenerationMessage(`生成完了！${data.images.length}枚の画像が作成されました。`)
        // You could display the images here if needed
        displayImages(data.images)
      }
      
    } catch (error) {
      console.error('Generation error:', error)
      setGenerationMessage(`エラーが発生しました: ${error.message}`)
    } finally {
      setIsGenerating(false)
    }
  }

  const displayImages = (base64Images) => {
    // Create a container for images
    const container = document.createElement('div')
    container.className = 'generated-images-preview'
    container.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: white;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.2);
      z-index: 1000;
      max-height: 80vh;
      overflow-y: auto;
      text-align: center;
    `
    
    const title = document.createElement('h3')
    title.textContent = '生成された画像'
    container.appendChild(title)
    
    const imagesContainer = document.createElement('div')
    imagesContainer.style.cssText = 'display: flex; gap: 10px; flex-wrap: wrap; justify-content: center;'
    
    base64Images.forEach((base64, index) => {
      const img = document.createElement('img')
      img.src = `data:image/png;base64,${base64}`
      img.style.cssText = 'width: 150px; height: auto; border: 1px solid #ddd;'
      img.alt = `Expression ${index + 1}`
      imagesContainer.appendChild(img)
    })
    
    container.appendChild(imagesContainer)
    
    const closeButton = document.createElement('button')
    closeButton.textContent = '閉じる'
    closeButton.style.cssText = `
      margin-top: 20px;
      padding: 10px 20px;
      background: #333;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    `
    closeButton.onclick = () => document.body.removeChild(container)
    container.appendChild(closeButton)
    
    document.body.appendChild(container)
  }

  return (
    <div className="generate-button-container">
      <button 
        onClick={handleGenerate}
        disabled={isGenerating}
        className="generate-button primary"
      >
        {isGenerating ? '生成中...' : 'ZIP形式で生成・ダウンロード'}
      </button>
      
      <button 
        onClick={handleGenerateBase64}
        disabled={isGenerating}
        className="generate-button secondary"
      >
        {isGenerating ? '生成中...' : 'プレビュー表示で生成'}
      </button>

      {downloadUrl && (
        <a 
          href={downloadUrl} 
          download={`standing_set_${characterData.character_id}.zip`}
          className="download-link"
        >
          再ダウンロード
        </a>
      )}
    </div>
  )
}

export default GenerateButton