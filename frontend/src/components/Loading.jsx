import './Loading.css'

function Loading({ message = 'Loading...', size = 'medium' }) {
  return (
    <div className={`loading-container size-${size}`}>
      <div className="spinner"></div>
      {message && <p className="loading-message">{message}</p>}
    </div>
  )
}

function LoadingSkeleton({ lines = 3, showAvatar = false }) {
  return (
    <div className="skeleton-container">
      {showAvatar && <div className="skeleton-avatar"></div>}
      <div className="skeleton-content">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className="skeleton-line"
            style={{ width: `${100 - i * 15}%` }}
          ></div>
        ))}
      </div>
    </div>
  )
}

export { Loading, LoadingSkeleton }
export default Loading
