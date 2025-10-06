import { useState } from 'react'
import './FantasyMode.css'

function FantasyMode({ generatedImages, setGeneratedImages, isGenerating, setIsGenerating }) {
  const [gender, setGender] = useState('female')
  const [height, setHeight] = useState('medium')
  const [hairLength, setHairLength] = useState('')
  const [hairColor, setHairColor] = useState('')
  const [hairStyle, setHairStyle] = useState('')
  const [outfit, setOutfit] = useState('')
  const [eyeShape, setEyeShape] = useState('')
  const [eyeColor, setEyeColor] = useState('')
  const [expression, setExpression] = useState('')
  const [error, setError] = useState('')
  const [outfitImage, setOutfitImage] = useState(null)
  const [outfitImageBase64, setOutfitImageBase64] = useState('')

  const handleOutfitImageUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    setError('')

    try {
      // 画像をbase64にエンコード
      const reader = new FileReader()
      reader.onload = (event) => {
        const base64String = event.target.result.split(',')[1] // data:image/xxx;base64, を除去
        setOutfitImageBase64(base64String)
        setOutfitImage(file)
      }
      reader.onerror = () => {
        setError('画像の読み込みに失敗しました')
        setOutfitImage(null)
        setOutfitImageBase64('')
      }
      reader.readAsDataURL(file)
    } catch (err) {
      console.error('Outfit image upload error:', err)
      setError(`画像のアップロードに失敗しました: ${err.message}`)
      setOutfitImage(null)
      setOutfitImageBase64('')
    }
  }

  const generateFantasyImages = async () => {
    // 服装は画像アップロードまたはテキスト入力のどちらかがあればOK
    const hasOutfit = outfit.trim() || outfitImageBase64

    if (!hairLength.trim() || !hairColor.trim() || !hairStyle.trim() ||
        !hasOutfit || !eyeShape.trim() || !eyeColor.trim() || !expression.trim()) {
      setError('すべての項目を入力してください（服装は画像アップロードまたはテキスト入力が必要です）')
      return
    }

    setIsGenerating(true)
    setError('')

    const fantasyCharacter = {
      character_id: `fantasy_${Date.now()}`,
      seed: Math.floor(Math.random() * 1000000),
      gender: gender,
      height: height,
      hair_length: hairLength,
      hair_color: hairColor,
      hair_style: hairStyle,
      outfit: outfit || 'default outfit',  // 画像がある場合はダミー値
      outfit_image_base64: outfitImageBase64 || null,
      eye_shape: eyeShape,
      eye_color: eyeColor,
      expression: expression
    }

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'https://standing-set-backend-545652287683.asia-northeast1.run.app'
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

  const downloadAllImages = () => {
    if (!generatedImages || generatedImages.length === 0) {
      setError('ダウンロードする画像がありません')
      return
    }

    // ファイル名の定義（画像の順番: 制服6枚 + 私服6枚）
    const fileNames = [
      // 制服セット (1-6)
      'uniform_nomal.png',
      'uniform_smile.png',
      'uniform_troubled.png',
      'uniform_big_smile.png',
      'uniform_sad.png',
      'uniform_angry.png',
      // 私服セット (7-12)
      'private_nomal.png',
      'private_smile.png',
      'private_troubled.png',
      'private_big_smile.png',
      'private_sad.png',
      'private_angry.png'
    ]

    // JSZipを使ってZIPファイルを作成
    import('jszip').then(({ default: JSZip }) => {
      const zip = new JSZip()

      generatedImages.forEach((base64Image, index) => {
        const fileName = fileNames[index] || `image_${index + 1}.png`
        // base64からバイナリデータに変換
        const imageData = base64Image.replace(/^data:image\/\w+;base64,/, '')
        zip.file(fileName, imageData, { base64: true })
      })

      // ZIPファイルを生成してダウンロード
      zip.generateAsync({ type: 'blob' }).then((content) => {
        const url = URL.createObjectURL(content)
        const link = document.createElement('a')
        link.href = url
        link.download = `fantasy_character_${Date.now()}.zip`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
      })
    }).catch((err) => {
      console.error('JSZip loading error:', err)
      setError('ダウンロードに失敗しました')
    })
  }

  const randomize = () => {
    // 性別に応じたランダムデータの配列
    const hairLengths = gender === 'male'
      ? ['short', 'medium', 'very short']
      : ['long', 'medium', 'short', 'very long', 'shoulder-length']

    const hairColors = [
      'black', 'dark brown', 'brown', 'light brown', 'chestnut',
      'blonde', 'platinum blonde', 'silver', 'white',
      'red', 'auburn', 'pink', 'purple', 'blue', 'green'
    ]

    const hairStyles = gender === 'male'
      ? ['short', 'messy', 'spiky', 'slicked back', 'crew cut', 'undercut',
         'side part', 'wavy', 'curly short', 'straight short']
      : ['straight', 'wavy', 'curly', 'ponytail', 'twintails', 'braided',
         'bob cut', 'pixie cut', 'messy', 'elegant updo', 'half-up',
         'side ponytail', 'twin braids', 'long flowing']

    const outfits = gender === 'male'
      ? ['knight armor', 'light armor', 'heavy armor', 'plate armor',
         'mage robe', 'wizard cloak', 'scholar outfit', 'war mage outfit',
         'adventurer gear', 'ranger outfit', 'thief outfit', 'assassin gear',
         'warrior outfit', 'samurai armor', 'eastern warrior', 'battle outfit',
         'casual fantasy outfit', 'mercenary gear']
      : ['knight armor', 'light armor', 'heavy armor', 'battle dress',
         'mage robe', 'wizard cloak', 'scholar outfit',
         'elegant dress', 'noble dress', 'princess gown', 'ball gown',
         'adventurer gear', 'ranger outfit', 'thief outfit',
         'priestess robe', 'nun outfit', 'shrine maiden',
         'fantasy kimono', 'eastern dress', 'casual fantasy outfit']

    const eyeShapes = gender === 'male'
      ? ['almond-shaped', 'narrow', 'sharp', 'gentle', 'determined', 'fierce']
      : ['large round', 'almond-shaped', 'narrow', 'upturned', 'droopy',
         'sharp', 'gentle', 'cat-like', 'innocent round']

    // 目の色は自然な色が多め（重み付け）
    const eyeColors = [
      ...['black', 'dark brown', 'brown'].flatMap(c => Array(5).fill(c)), // 自然な色を5倍
      ...['navy blue', 'dark blue'].flatMap(c => Array(3).fill(c)), // 紺系を3倍
      ...['gray', 'dark gray'].flatMap(c => Array(2).fill(c)), // グレー系を2倍
      'hazel', 'amber', 'green', 'light brown',
      'blue', 'violet', 'red', 'gold', 'silver',
      'heterochromia (brown and blue)', 'heterochromia (green and brown)'
    ]

    const expressions = gender === 'male'
      ? ['confident', 'mysterious', 'serious', 'proud', 'determined',
         'calm', 'fierce', 'aloof', 'stoic', 'battle-ready', 'focused']
      : ['confident', 'mysterious', 'gentle', 'cheerful', 'serious',
         'shy', 'proud', 'determined', 'melancholic', 'playful',
         'calm', 'fierce', 'kind', 'aloof', 'charming']

    const heights = ['small', 'medium', 'tall']

    // ランダムに選択
    const randomChoice = (arr) => arr[Math.floor(Math.random() * arr.length)]

    setHairLength(randomChoice(hairLengths))
    setHairColor(randomChoice(hairColors))
    setHairStyle(randomChoice(hairStyles))
    setOutfit(randomChoice(outfits))
    setEyeShape(randomChoice(eyeShapes))
    setEyeColor(randomChoice(eyeColors))
    setExpression(randomChoice(expressions))
    setHeight(randomChoice(heights))
    setError('')
  }

  const reset = () => {
    setGender('female')
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
    setOutfitImage(null)
    setOutfitImageBase64('')
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
            <label>性別</label>
            <div className="height-buttons">
              <button
                className={`height-btn ${gender === 'female' ? 'active' : ''}`}
                onClick={() => setGender('female')}
              >
                女性
              </button>
              <button
                className={`height-btn ${gender === 'male' ? 'active' : ''}`}
                onClick={() => setGender('male')}
              >
                男性
              </button>
            </div>
          </div>

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

          {!outfitImageBase64 && (
            <div className="form-group">
              <label>服装（またはテキストの代わりに画像アップロード）</label>
              <input
                type="text"
                value={outfit}
                onChange={(e) => setOutfit(e.target.value)}
                placeholder="例: knight armor, mage robe, elegant dress"
                className="fantasy-input"
              />
            </div>
          )}

          <div className="form-group">
            <label>服装画像をアップロード{!outfitImageBase64 && '（オプション）'}</label>
            <input
              type="file"
              accept="image/*"
              onChange={handleOutfitImageUpload}
              className="fantasy-input-file"
              disabled={isGenerating}
            />
            {outfitImageBase64 && (
              <div className="outfit-analysis-result">
                ✓ 画像アップロード完了: {outfitImage.name}
                <button
                  onClick={() => {
                    setOutfitImageBase64('')
                    setOutfitImage(null)
                  }}
                  className="remove-image-btn"
                  disabled={isGenerating}
                >
                  × 削除
                </button>
              </div>
            )}
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
              onClick={randomize}
              className="random-button"
              disabled={isGenerating}
            >
              🎲 ランダム入力
            </button>
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
            <button
              onClick={downloadAllImages}
              className="download-button"
              disabled={isGenerating || !generatedImages || generatedImages.length === 0}
            >
              12枚まとめてダウンロード (ZIP)
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default FantasyMode