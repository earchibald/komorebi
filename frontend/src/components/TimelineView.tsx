/**
 * TimelineView - Chunks grouped by time buckets with granularity toggle
 * 
 * Shows a horizontal bar chart of chunk activity over time.
 * Supports day/week/month granularity and project filtering.
 */

import { useEffect, useState } from 'react'
import {
  timeline,
  timelineLoading,
  timelineGranularity,
  fetchTimeline,
  projects,
  fetchProjects,
  selectChunk,
  chunks,
} from '../store'
import type { Chunk, TimelineBucket } from '../store'

type Granularity = 'day' | 'week' | 'month'

export function TimelineView() {
  const [projectFilter, setProjectFilter] = useState('')
  const [expandedBucket, setExpandedBucket] = useState<string | null>(null)

  useEffect(() => {
    fetchTimeline(timelineGranularity.value)
    fetchProjects()
  }, [])

  const handleGranularityChange = (g: Granularity) => {
    timelineGranularity.value = g
    fetchTimeline(g, undefined, projectFilter || undefined)
  }

  const handleProjectFilter = (projectId: string) => {
    setProjectFilter(projectId)
    fetchTimeline(timelineGranularity.value, undefined, projectId || undefined)
  }

  const toggleBucket = (label: string) => {
    setExpandedBucket(expandedBucket === label ? null : label)
  }

  // Read signal values outside JSX
  const timelineData = timeline.value
  const isLoading = timelineLoading.value
  const granularity = timelineGranularity.value
  const projectList = projects.value
  const allChunks = chunks.value

  const maxCount = timelineData
    ? Math.max(...timelineData.buckets.map(b => b.chunk_count), 1)
    : 1

  return (
    <div className="timeline-view">
      {/* Controls */}
      <div className="timeline-controls">
        <div className="granularity-toggle">
          {(['day', 'week', 'month'] as Granularity[]).map(g => (
            <button
              key={g}
              className={`tab ${granularity === g ? 'active' : ''}`}
              onClick={() => handleGranularityChange(g)}
            >
              {g.charAt(0).toUpperCase() + g.slice(1)}
            </button>
          ))}
        </div>
        <select
          className="timeline-project-filter"
          value={projectFilter}
          onChange={(e) => handleProjectFilter(e.target.value)}
        >
          <option value="">All Projects</option>
          {projectList.map(p => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="loading">Loading timeline...</div>
      )}

      {/* Empty */}
      {!isLoading && timelineData && timelineData.buckets.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">📅</div>
          <p>No activity in the selected time range.</p>
        </div>
      )}

      {/* Timeline Chart */}
      {!isLoading && timelineData && timelineData.buckets.length > 0 && (
        <div className="timeline-chart">
          <div className="timeline-summary">
            <span>{timelineData.total_chunks} chunks across {timelineData.buckets.length} {granularity}s</span>
          </div>

          {timelineData.buckets.map((bucket: TimelineBucket) => (
            <div key={bucket.bucket_label} className="timeline-bucket">
              <div
                className="timeline-bar-row"
                onClick={() => toggleBucket(bucket.bucket_label)}
                role="button"
                tabIndex={0}
              >
                <span className="timeline-bar-label">{bucket.bucket_label}</span>
                <div className="timeline-bar-track">
                  <div
                    className="timeline-bar-fill"
                    style={{ width: `${(bucket.chunk_count / maxCount) * 100}%` }}
                  >
                    {/* Status color segments */}
                    {Object.entries(bucket.by_status).map(([status, count]) => (
                      <div
                        key={status}
                        className={`timeline-bar-segment status-${status}`}
                        style={{ flex: count }}
                        title={`${status}: ${count}`}
                      />
                    ))}
                  </div>
                </div>
                <span className="timeline-bar-count">{bucket.chunk_count}</span>
              </div>

              {/* Expanded chunk previews */}
              {expandedBucket === bucket.bucket_label && (
                <div className="timeline-bucket-detail">
                  {bucket.chunk_ids.map(id => {
                    const chunk = allChunks.find((c: Chunk) => c.id === id)
                    if (!chunk) return (
                      <div key={id} className="timeline-chunk-preview">
                        <span className="chunk-id">{id.slice(0, 8)}...</span>
                      </div>
                    )
                    return (
                      <div
                        key={id}
                        className="timeline-chunk-preview chunk-item-clickable"
                        onClick={() => selectChunk(chunk)}
                      >
                        <span className={`chunk-status ${chunk.status}`}>{chunk.status}</span>
                        <span className="timeline-chunk-content">
                          {chunk.content.length > 100 ? chunk.content.slice(0, 100) + '...' : chunk.content}
                        </span>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
