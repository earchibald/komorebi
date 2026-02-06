/**
 * WatcherStatus — Active filesystem watchers + recent file events
 *
 * Shows which directories are being watched by `k watch` and
 * a timeline of recent filesystem changes.
 */

import { useEffect } from 'react'
import {
  recentFileEvents,
  activeTrace,
  fetchFileEvents,
  fetchActiveTrace,
} from '../store/oracle'

const OP_ICONS: Record<string, string> = {
  created: '🟢',
  modified: '🟡',
  deleted: '🔴',
  moved: '🔵',
}

export function WatcherStatus() {
  useEffect(() => {
    fetchActiveTrace()
    fetchFileEvents()
  }, [])

  const events = recentFileEvents.value

  return (
    <div className="watcher-status">
      <h2>👁️ Filesystem Watcher</h2>

      {/* Active Trace */}
      <div style={{
        background: 'var(--card-bg, #f8f8f8)',
        padding: '12px 16px',
        borderRadius: '8px',
        marginBottom: '16px',
      }}>
        <strong>Active Trace:</strong>{' '}
        {activeTrace.value ? (
          <span style={{ fontFamily: 'monospace' }}>
            {activeTrace.value.name} ({activeTrace.value.chunk_count} chunks)
          </span>
        ) : (
          <span style={{ color: 'var(--text-muted)' }}>None — create one with `k switch &lt;name&gt;`</span>
        )}
      </div>

      {/* Recent File Events */}
      <h3>Recent File Events</h3>
      {events.length === 0 ? (
        <p style={{ color: 'var(--text-muted)' }}>
          No file events recorded. Start a watcher with <code>k watch ./path</code>
        </p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9em' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid var(--border)' }}>
              <th style={{ textAlign: 'left', padding: '6px' }}>Op</th>
              <th style={{ textAlign: 'left', padding: '6px' }}>Path</th>
              <th style={{ textAlign: 'right', padding: '6px' }}>Size</th>
              <th style={{ textAlign: 'left', padding: '6px' }}>Type</th>
              <th style={{ textAlign: 'left', padding: '6px' }}>Time</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id} style={{ borderBottom: '1px solid var(--border)' }}>
                <td style={{ padding: '6px' }}>
                  {OP_ICONS[e.crud_op] || '⚪'} {e.crud_op}
                </td>
                <td style={{ padding: '6px', fontFamily: 'monospace', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {e.path}
                </td>
                <td style={{ textAlign: 'right', padding: '6px' }}>
                  {e.size_bytes != null ? formatBytes(e.size_bytes) : '-'}
                </td>
                <td style={{ padding: '6px' }}>{e.mime_type || '-'}</td>
                <td style={{ padding: '6px' }}>
                  {new Date(e.created_at).toLocaleTimeString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
