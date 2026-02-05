import { useEffect, useState } from 'react'
import { chunks, loading, fetchChunks } from '../store'
import type { Chunk } from '../store'

type StatusFilter = 'all' | 'inbox' | 'processed' | 'compacted' | 'archived'

export function ChunkList() {
  const [filter, setFilter] = useState<StatusFilter>('all')

  useEffect(() => {
    fetchChunks(filter === 'all' ? undefined : filter)
  }, [filter])

  const filteredChunks = filter === 'all' 
    ? chunks.value 
    : chunks.value.filter(c => c.status === filter)

  return (
    <div>
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        {(['all', 'inbox', 'processed', 'compacted', 'archived'] as StatusFilter[]).map(status => (
          <button
            key={status}
            className={`tab ${filter === status ? 'active' : ''}`}
            onClick={() => setFilter(status)}
            style={{ padding: '0.5rem 1rem', fontSize: '0.9rem' }}
          >
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </button>
        ))}
      </div>

      {loading.value && filteredChunks.length === 0 ? (
        <div className="loading">Loading chunks...</div>
      ) : filteredChunks.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📋</div>
          <p>No chunks found with filter: {filter}</p>
        </div>
      ) : (
        <div className="chunk-list">
          {filteredChunks.map((chunk: Chunk) => (
            <div key={chunk.id} className="chunk-item">
              <div className="chunk-header">
                <span className="chunk-id">{chunk.id.slice(0, 8)}...</span>
                <span className={`chunk-status ${chunk.status}`}>{chunk.status}</span>
              </div>
              <div className="chunk-content">{chunk.content}</div>
              {chunk.summary && (
                <div style={{ color: 'var(--accent-green)', fontSize: '0.9rem', marginTop: '0.5rem' }}>
                  💡 {chunk.summary}
                </div>
              )}
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
                {chunk.token_count && <span>🔢 {chunk.token_count} tokens</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
