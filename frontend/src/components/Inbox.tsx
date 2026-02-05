import { useState, useEffect, FormEvent } from 'react'
import { chunks, loading, captureChunk, fetchChunks, connectSSE, disconnectSSE } from '../store'
import type { Chunk } from '../store'

export function Inbox() {
  const [content, setContent] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    // Fetch inbox chunks and connect to SSE
    // SSE will handle stats updates, so we don't need to fetch them here
    fetchChunks('inbox')
    connectSSE()
    return () => disconnectSSE()
  }, [])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!content.trim() || isSubmitting) return

    setIsSubmitting(true)
    try {
      await captureChunk(content.trim())
      setContent('')
    } catch {
      // Error handled in store
    } finally {
      setIsSubmitting(false)
    }
  }

  const inboxChunks = chunks.value.filter(c => c.status === 'inbox')

  return (
    <div>
      <h2>Quick Capture</h2>
      <form className="inbox-form" onSubmit={handleSubmit}>
        <input
          className="inbox-input"
          type="text"
          placeholder="Capture a thought, task, or idea..."
          value={content}
          onChange={(e) => setContent(e.target.value)}
          disabled={isSubmitting}
        />
        <button
          className="inbox-button"
          type="submit"
          disabled={isSubmitting || !content.trim()}
        >
          {isSubmitting ? '...' : '📝 Capture'}
        </button>
      </form>

      {loading.value && inboxChunks.length === 0 ? (
        <div className="loading">Loading inbox...</div>
      ) : inboxChunks.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📭</div>
          <p>Your inbox is empty. Capture something!</p>
        </div>
      ) : (
        <div className="chunk-list">
          {inboxChunks.map((chunk: Chunk) => (
            <div key={chunk.id} className="chunk-item">
              <div className="chunk-header">
                <span className="chunk-id">{chunk.id.slice(0, 8)}...</span>
                <span className={`chunk-status ${chunk.status}`}>{chunk.status}</span>
              </div>
              <div className="chunk-content">{chunk.content}</div>
              {chunk.tags.length > 0 && (
                <div className="chunk-tags">
                  {chunk.tags.map(tag => (
                    <span key={tag} className="chunk-tag">{tag}</span>
                  ))}
                </div>
              )}
              <div className="chunk-meta">
                <span>📅 {new Date(chunk.created_at).toLocaleString()}</span>
                {chunk.source && <span>📌 {chunk.source}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
