import { useEffect, useState, useMemo } from 'react'
import { 
  chunks, 
  loading, 
  fetchChunks, 
  selectChunk, 
  searchResults, 
  searchLoading, 
  isSearchActive 
} from '../store'
import type { Chunk } from '../store'
import { SearchBar } from './SearchBar'
import { FilterPanel } from './FilterPanel'

type StatusFilter = 'all' | 'inbox' | 'processed' | 'compacted' | 'archived'

export function ChunkList() {
  const [filter, setFilter] = useState<StatusFilter>('all')

  // Fetch ALL chunks once on mount - no status filter
  useEffect(() => {
    fetchChunks(undefined, 500) // Fetch up to 500 chunks
  }, []) // Only runs once on mount

  // Read signal values in render body for proper @preact/signals-react v2 subscriptions.
  // Reading .value inside useMemo callbacks does NOT create subscriptions.
  const searchActive = isSearchActive.value
  const results = searchResults.value
  const allChunks = chunks.value
  const isSearchLoadingVal = searchLoading.value
  const isChunksLoading = loading.value

  // Determine which chunks to display
  const displayChunks = useMemo(() => {
    // Start with search results if search is active, otherwise all chunks
    let base: Chunk[]
    if (searchActive && results) {
      base = results.items
    } else {
      base = allChunks
    }
    // Apply local tab filter on top (works with both search and non-search)
    if (filter === 'all') return base
    return base.filter(c => c.status === filter)
  }, [allChunks, filter, searchActive, results])

  const isLoading = searchActive ? isSearchLoadingVal : (isChunksLoading && allChunks.length === 0)

  return (
    <div>
      {/* Search UI */}
      <SearchBar />
      <FilterPanel />

      {/* Status Tabs - Always visible; applies client-side filter on top of search results */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', marginTop: '1rem' }}>
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

      {/* Loading State */}
      {isLoading ? (
        <div className="loading">
          {searchActive ? 'Searching...' : 'Loading chunks...'}
        </div>
      ) : displayChunks.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📋</div>
          <p>
            {searchActive
              ? `No results found${filter !== 'all' ? ` with status "${filter}"` : ''}. Try adjusting your search or filter.`
              : `No chunks found with filter: ${filter}`
            }
          </p>
        </div>
      ) : (
        <div className="chunk-list">
          {displayChunks.map((chunk: Chunk) => (
            <div key={chunk.id} className="chunk-item chunk-item-clickable" onClick={() => selectChunk(chunk)}>
              <div className="chunk-header">
                <span className="chunk-id">{chunk.id.slice(0, 8)}...</span>
                <span className={`chunk-status ${chunk.status}`}>{chunk.status}</span>
              </div>
              <div className="chunk-content" title={chunk.content}>
                {chunk.content.length > 200 ? chunk.content.slice(0, 200) + '...' : chunk.content}
              </div>
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
