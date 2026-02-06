import { useEffect } from 'react'
import { stats, fetchStats } from '../store'

export function Stats() {
  useEffect(() => {
    fetchStats()
    // Refresh stats every 60 seconds (reduced from 30)
    const interval = setInterval(fetchStats, 60000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="stats">
      <div className="stat-card">
        <div className="stat-value">{stats.value.inbox}</div>
        <div className="stat-label">📥 Inbox</div>
      </div>
      <div className="stat-card">
        <div className="stat-value">{stats.value.processed}</div>
        <div className="stat-label">⚙️ Processed</div>
      </div>
      <div className="stat-card">
        <div className="stat-value">{stats.value.compacted}</div>
        <div className="stat-label">📦 Compacted</div>
      </div>
      <div className="stat-card">
        <div className="stat-value">{stats.value.archived}</div>
        <div className="stat-label">🗄️ Archived</div>
      </div>
      <div className="stat-card">
        <div className="stat-value">{stats.value.total}</div>
        <div className="stat-label">📊 Total</div>
      </div>
    </div>
  )
}
