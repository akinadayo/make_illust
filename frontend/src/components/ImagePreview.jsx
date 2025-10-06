import './ImagePreview.css'

function ImagePreview({ images }) {
  const expressions = [
    // 制服セット (1-6)
    '制服 - ニュートラル',
    '制服 - 微笑み',
    '制服 - 困り顔',
    '制服 - 満面の笑み',
    '制服 - 悲しい',
    '制服 - 真剣',
    // 私服セット (7-12)
    '私服 - ニュートラル',
    '私服 - 微笑み',
    '私服 - 困り顔',
    '私服 - 満面の笑み',
    '私服 - 悲しい',
    '私服 - 真剣'
  ]

  return (
    <div className="image-preview">
      <h2>生成された立ち絵</h2>
      <div className="images-grid">
        {images.map((image, index) => (
          <div key={index} className="image-card">
            <img
              src={`data:image/png;base64,${image}`}
              alt={expressions[index] || `画像 ${index + 1}`}
            />
            <p>{expressions[index] || `画像 ${index + 1}`}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ImagePreview