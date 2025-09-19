import './ImagePreview.css'

function ImagePreview({ images }) {
  const expressions = [
    'ニュートラル',
    '微笑み',
    '驚き',
    '困り顔',
    'むすっ'
  ]

  return (
    <div className="image-preview">
      <h2>生成された立ち絵</h2>
      <div className="images-grid">
        {images.map((image, index) => (
          <div key={index} className="image-card">
            <img 
              src={`data:image/png;base64,${image}`} 
              alt={expressions[index]}
            />
            <p>{expressions[index]}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ImagePreview