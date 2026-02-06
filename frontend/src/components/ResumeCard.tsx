import {
  briefing,
  briefingLoading,
  briefingError,
  fetchBriefing,
  clearBriefing,
  selectChunk,
} from '../store'
import type { Chunk, Entity } from '../store'

interface ResumeCardProps {
  projectId: string
  onClose: () => void
}

export function ResumeCard({ projectId, onClose }: ResumeCardProps) {
  const data = briefing.value
  const isLoading = briefingLoading.value
  const err = briefingError.value

  // Auto-fetch on first render if not already loaded for this project
  if (!data && !isLoading && !err) {
    fetchBriefing(projectId)
  }

  const handleRetry = () => {
    clearBriefing()
    fetchBriefing(projectId)
  }

  const handleClose = () => {
    clearBriefing()
    onClose()
  }

  const handleChunkClick = (chunk: Chunk) => {
    selectChunk(chunk)
  }

  // Loading skeleton
  if (isLoading) {
    return (
      <div className="resume-card">
        <div className="resume-header">
          <span className="resume-title">Context Resume</span>
          <button className="resume-close" onClick={handleClose} title="Close">
            &times;
          </button>
        </div>
        <div className="resume-skeleton">
          <div className="skeleton-line skeleton-line--long" />
          <div className="skeleton-line skeleton-line--medium" />
          <div className="skeleton-line skeleton-line--short" />
        </div>
      </div>
    )
  }

  // Error state
  if (err) {
    return (
      <div className="resume-card resume-card--error">
        <div className="resume-header">
          <span className="resume-title">Context Resume</span>
          <button className="resume-close" onClick={handleClose} title="Close">
            &times;
          </button>
        </div>
        <p className="resume-error-text">{err}</p>
        <button className="resume-retry-btn" onClick={handleRetry}>
          Retry
        </button>
      </div>
    )
  }

  // No data yet (shouldn't happen due to auto-fetch, but safety)
  if (!data) return null

  return (
    <div className="resume-card">
      <div className="resume-header">
        <span className="resume-title">Context Resume</span>
        <span className="resume-timestamp">
          {new Date(data.generated_at).toLocaleString()}
        </span>
        <button className="resume-close" onClick={handleClose} title="Close">
          &times;
        </button>
      </div>

      {/* LLM availability badge */}
      {!data.ollama_available && (
        <div className="resume-badge resume-badge--fallback">
          Template mode (Ollama offline)
        </div>
      )}

      {/* Summary */}
      <div className="resume-summary">
        {data.summary.split('\n').map((line: string, i: number) => (
          <p key={i} className="resume-summary-line">
            {line}
          </p>
        ))}
      </div>

      {/* Sections grid */}
      <div className="resume-sections">
        {/* Last active item */}
        {data.recent_chunks.length > 0 && (
          <div className="resume-section">
            <h4 className="resume-section-heading">Last Active Item</h4>
            <p className="resume-section-content">
              {data.recent_chunks[0].summary || data.recent_chunks[0].content.slice(0, 120)}
            </p>
            <button
              className="resume-jump-btn"
              onClick={() => handleChunkClick(data.recent_chunks[0])}
            >
              Open last chunk
            </button>
          </div>
        )}

        {/* Recent decisions */}
        {data.decisions.length > 0 && (
          <div className="resume-section">
            <h4 className="resume-section-heading">Recent Decisions</h4>
            <ul className="resume-decision-list">
              {data.decisions.slice(0, 5).map((d: Entity, i: number) => (
                <li key={i} className="resume-decision-item">
                  {d.value}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Related context */}
      {data.related_context.length > 0 && (
        <div className="resume-related">
          <h4 className="resume-section-heading">Related Context</h4>
          {data.related_context.slice(0, 3).map((snippet: string, i: number) => (
            <p key={i} className="resume-related-snippet">
              {snippet.slice(0, 150)}
              {snippet.length > 150 && '...'}
            </p>
          ))}
        </div>
      )}

      {/* Context window usage */}
      {data.context_window_usage !== null && (
        <div className="resume-meta">
          Context window: {Math.round(data.context_window_usage * 100)}%
        </div>
      )}
    </div>
  )
}
