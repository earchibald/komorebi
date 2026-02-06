import { selectedChunk, chunkEntities, entitiesLoading, closeDrawer } from '../store'
import type { Entity } from '../store'

const ENTITY_TYPE_CONFIG: Record<string, { label: string; icon: string; color: string }> = {
  error: { label: 'Error', icon: '🐛', color: 'var(--accent-pink)' },
  url: { label: 'URL', icon: '🔗', color: 'var(--accent-blue)' },
  tool_id: { label: 'Tool', icon: '🔧', color: 'var(--accent-yellow)' },
  decision: { label: 'Decision', icon: '⚖️', color: 'var(--accent-green)' },
  code_ref: { label: 'Code', icon: '💻', color: '#c792ea' },
}

function EntityBadge({ entity }: { entity: Entity }) {
  const config = ENTITY_TYPE_CONFIG[entity.entity_type] || {
    label: entity.entity_type,
    icon: '📌',
    color: 'var(--text-secondary)',
  }

  return (
    <div className="entity-item">
      <div className="entity-header">
        <span className="entity-badge" style={{ borderColor: config.color }}>
          {config.icon} {config.label}
        </span>
        <span className="entity-confidence" title={`Confidence: ${Math.round(entity.confidence * 100)}%`}>
          <span
            className="confidence-bar"
            style={{ width: `${entity.confidence * 100}%`, background: config.color }}
          />
        </span>
      </div>
      <div className="entity-value">{entity.value}</div>
      {entity.context_snippet && (
        <div className="entity-context">{entity.context_snippet}</div>
      )}
    </div>
  )
}

export function ChunkDrawer() {
  const chunk = selectedChunk.value
  if (!chunk) return null

  const handleOverlayClick = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).classList.contains('drawer-overlay')) {
      closeDrawer()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') closeDrawer()
  }

  const entities = chunkEntities.value
  const isLoading = entitiesLoading.value

  // Group entities by type
  const grouped: Record<string, Entity[]> = {}
  entities.forEach((e) => {
    if (!grouped[e.entity_type]) grouped[e.entity_type] = []
    grouped[e.entity_type].push(e)
  })

  return (
    <div
      className="drawer-overlay"
      onClick={handleOverlayClick}
      onKeyDown={handleKeyDown}
      role="dialog"
      aria-label="Chunk detail"
      tabIndex={-1}
    >
      <aside className="drawer-panel">
        <div className="drawer-header">
          <div>
            <h3>Chunk Detail</h3>
            <span className="chunk-id" style={{ fontSize: '0.75rem' }}>
              {chunk.id}
            </span>
          </div>
          <button className="drawer-close" onClick={closeDrawer} aria-label="Close drawer">
            ✕
          </button>
        </div>

        <div className="drawer-body">
          {/* Status + Meta */}
          <div className="drawer-meta">
            <span className={`chunk-status ${chunk.status}`}>{chunk.status}</span>
            {chunk.source && <span className="drawer-meta-item">📌 {chunk.source}</span>}
            {chunk.token_count && (
              <span className="drawer-meta-item">🔢 {chunk.token_count} tokens</span>
            )}
            <span className="drawer-meta-item">
              📅 {new Date(chunk.created_at).toLocaleString()}
            </span>
          </div>

          {/* Full Content */}
          <section className="drawer-section">
            <h4>Content</h4>
            <pre className="drawer-content">{chunk.content}</pre>
          </section>

          {/* Summary */}
          {chunk.summary && (
            <section className="drawer-section">
              <h4>Summary</h4>
              <p className="drawer-summary">{chunk.summary}</p>
            </section>
          )}

          {/* Tags */}
          {chunk.tags.length > 0 && (
            <section className="drawer-section">
              <h4>Tags</h4>
              <div className="chunk-tags">
                {chunk.tags.map((tag) => (
                  <span key={tag} className="chunk-tag">
                    {tag}
                  </span>
                ))}
              </div>
            </section>
          )}

          {/* Entities */}
          <section className="drawer-section">
            <h4>
              Extracted Entities
              {entities.length > 0 && (
                <span className="entity-count">{entities.length}</span>
              )}
            </h4>
            {isLoading ? (
              <div className="loading" style={{ padding: '1rem 0' }}>
                Loading entities...
              </div>
            ) : entities.length === 0 ? (
              <p className="drawer-empty">No entities extracted from this chunk.</p>
            ) : (
              <div className="entity-list">
                {Object.entries(grouped).map(([type, typeEntities]) => (
                  <div key={type} className="entity-group">
                    {typeEntities.map((entity) => (
                      <EntityBadge key={entity.id} entity={entity} />
                    ))}
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </aside>
    </div>
  )
}
