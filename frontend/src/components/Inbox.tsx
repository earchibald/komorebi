import { useState, useEffect, useMemo, FormEvent } from 'react'
import { chunks, loading, captureChunk, fetchChunks, connectSSE, disconnectSSE, selectChunk } from '../store'
import type { Chunk } from '../store'

type SortOrder = 'newest' | 'oldest'

function getAgeDays(dateStr: string): number {
  const created = new Date(dateStr)
  const now = new Date()
  return Math.floor((now.getTime() - created.getTime()) / (1000 * 60 * 60 * 24))
}

function getAgeIndicator(dateStr: string): string {
  const days = getAgeDays(dateStr)
  if (days > 7) return '🔴'
  if (days >= 2) return '🟡'
  return '🟢'
}

function formatAge(dateStr: string): string {
  const days = getAgeDays(dateStr)
  if (days === 0) return 'today'
  if (days === 1) return '1 day ago'
  return `${days} days ago`
}

export function Inbox() {
  const [content, setContent] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [sortOrder, setSortOrder] = useState<SortOrder>('newest')

  useEffect(() => {
    fetchChunks(undefined, 500)
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

  const inboxChunks = useMemo(() => {
    const filtered = chunks.value.filter(c => c.status === 'inbox')
    return filtered.sort((a, b) => {
      const dateA = new Date(a.created_at).getTime()
      const dateB = new Date(b.created_at).getTime()
      return sortOrder === 'newest' ? dateB - dateA : dateA - dateB
    })
  }, [chunks.value, sortOrder])

  const oldestAge = inboxChunks.length > 0
    ? Math.max(...inboxChunks.map(c => getAgeDays(c.created_at)))
    : null

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

      {/* Inbox Header */}
      {inboxChunks.length > 0 && (
        <div className="inbox-header">
          <div className="inbox-header-info">
            <span className="inbox-count">
              ℹ️ {inboxChunks.length} inbox item{inboxChunks.length !== 1 ? 's' : ''}
            </span>
            {oldestAge !== null && oldestAge > 0 && (
              <span className="inbox-oldest">
                Oldest: {oldestAge} day{oldestAge !== 1 ? 's' : ''} ago
              </span>
            )}
          </div>
          <div className="inbox-header-controls">
            <select
              className="inbox-sort"
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value as SortOrder)}
            >
              <option value="newest">Sort: Newest</option>
              <option value="oldest">Sort: Oldest</option>
            </select>
          </div>
        </div>
      )}

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
            <div key={chunk.id} className="chunk-item chunk-item-clickable" onClick={() => selectChunk(chunk)}>
              <div className="chunk-header">
                <span className="chunk-age-indicator" title={formatAge(chunk.created_at)}>
                  {getAgeIndicator(chunk.created_at)}
                </span>
                <span className="chunk-id">{chunk.id.slice(0, 8)}...</span>
                <span className="chunk-age-text">({formatAge(chunk.created_at)})</span>
                <span className={`chunk-status ${chunk.status}`}>{chunk.status}</span>
              </div>
              <div className="chunk-content" title={chunk.content}>
                {chunk.content.length > 200 ? chunk.content.slice(0, 200) + '...' : chunk.content}
              </div>
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
