/**
 * StatsDashboard - Enhanced statistics with weekly chart and insights
 * 
 * Replaces the simple Stats component with weekly trends,
 * per-project breakdown, and actionable insights.
 */

import { useEffect } from 'react'
import { stats, fetchStats } from '../store'
import type { DashboardStats } from '../store'

export function StatsDashboard() {
  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 60000)
    return () => clearInterval(interval)
  }, [])

  const s: DashboardStats = stats.value

  const maxWeekCount = Math.max(...s.by_week.map(w => w.count), 1)

  return (
    <div className="stats-dashboard">
      {/* Summary Cards */}
      <div className="stats">
        <div className="stat-card">
          <div className="stat-value">{s.inbox}</div>
          <div className="stat-label">📥 Inbox</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{s.processed}</div>
          <div className="stat-label">⚙️ Processed</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{s.compacted}</div>
          <div className="stat-label">📦 Compacted</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{s.archived}</div>
          <div className="stat-label">🗄️ Archived</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{s.total}</div>
          <div className="stat-label">📊 Total</div>
        </div>
      </div>

      {/* Weekly Activity Chart */}
      {s.by_week.length > 0 && (
        <section className="dashboard-section">
          <h3>📈 Weekly Activity (past 8 weeks)</h3>
          <div className="week-chart">
            {s.by_week.map(week => (
              <div className="week-bar-row" key={week.week_start}>
                <span className="week-bar-label">{week.week_start}</span>
                <div className="week-bar-track">
                  <div
                    className="week-bar-fill"
                    style={{ width: `${(week.count / maxWeekCount) * 100}%` }}
                  />
                </div>
                <span className="week-bar-count">{week.count}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Insights */}
      <section className="dashboard-section">
        <h3>💡 Insights</h3>
        <div className="insights-list">
          {s.oldest_inbox_age_days !== null && (
            <div className="insight-item">
              <span className="insight-icon">
                {s.oldest_inbox_age_days > 7 ? '🔴' : s.oldest_inbox_age_days > 2 ? '🟡' : '🟢'}
              </span>
              <span>Oldest inbox item: <strong>{s.oldest_inbox_age_days} day{s.oldest_inbox_age_days !== 1 ? 's' : ''}</strong> old</span>
            </div>
          )}
          {s.most_active_project && (
            <div className="insight-item">
              <span className="insight-icon">📁</span>
              <span>Most active project: <strong>{s.most_active_project}</strong> ({s.most_active_project_count} chunks)</span>
            </div>
          )}
          <div className="insight-item">
            <span className="insight-icon">🏷️</span>
            <span><strong>{s.entity_count}</strong> entities extracted</span>
          </div>
        </div>
      </section>

      {/* Per-Project Breakdown */}
      {s.by_project.length > 0 && (
        <section className="dashboard-section">
          <h3>📁 Projects</h3>
          <div className="project-breakdown">
            {s.by_project.map(proj => (
              <div className="project-row" key={proj.id}>
                <span className="project-name">{proj.name}</span>
                <span className="project-count">{proj.chunk_count} chunks</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
