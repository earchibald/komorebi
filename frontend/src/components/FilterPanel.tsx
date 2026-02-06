/**
 * FilterPanel - Advanced search filters for chunks
 * 
 * Uses local React state bridges to avoid signal/React controlled input race condition.
 */

import { useState, useEffect } from 'react'
import { searchFilters, projects, debouncedSearch, clearSearch } from '../store'

export function FilterPanel() {
  const [isExpanded, setIsExpanded] = useState(false)

  // Local state bridges for filter inputs (status dropdown removed — ChunkList tabs handle status)
  const [localProjectId, setLocalProjectId] = useState(searchFilters.value.projectId || '')
  const [localEntityType, setLocalEntityType] = useState(searchFilters.value.entityType || '')
  const [localEntityValue, setLocalEntityValue] = useState(searchFilters.value.entityValue || '')
  const [localCreatedAfter, setLocalCreatedAfter] = useState(searchFilters.value.createdAfter || '')
  const [localCreatedBefore, setLocalCreatedBefore] = useState(searchFilters.value.createdBefore || '')

  // Sync signal → local state when signal changes externally (e.g., clearSearch)
  useEffect(() => {
    const filters = searchFilters.value
    setLocalProjectId(filters.projectId || '')
    setLocalEntityType(filters.entityType || '')
    setLocalEntityValue(filters.entityValue || '')
    setLocalCreatedAfter(filters.createdAfter || '')
    setLocalCreatedBefore(filters.createdBefore || '')
  }, [searchFilters.value])

  const updateFilter = <K extends keyof typeof searchFilters.value>(
    key: K,
    value: typeof searchFilters.value[K]
  ) => {
    if (value) {
      searchFilters.value = { ...searchFilters.value, [key]: value }
    } else {
      const { [key]: _, ...rest } = searchFilters.value
      searchFilters.value = rest
    }
    debouncedSearch()
  }

  const handleClearFilters = () => {
    clearSearch()
    setIsExpanded(false)
  }

  const activeFilterCount = Object.keys(searchFilters.value).length

  // Read projects value outside JSX
  const projectList = projects.value

  return (
    <div className="filter-panel">
      <button 
        className={`filter-toggle ${isExpanded ? 'expanded' : ''}`}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span>🔧 Filters</span>
        {activeFilterCount > 0 && (
          <span className="filter-badge">{activeFilterCount}</span>
        )}
        <span className="toggle-icon">{isExpanded ? '▲' : '▼'}</span>
      </button>

      {isExpanded && (
        <div className="filter-content">
          <div className="filter-grid">
            {/* Status filter removed — ChunkList tabs handle status filtering */}

            {/* Project Filter */}
            <div className="filter-field">
              <label htmlFor="filter-project">Project</label>
              <select
                id="filter-project"
                value={localProjectId}
                onChange={(e) => {
                  setLocalProjectId(e.target.value)
                  updateFilter('projectId', e.target.value || undefined)
                }}
              >
                <option value="">All Projects</option>
                {projectList.map(project => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Entity Type Filter */}
            <div className="filter-field">
              <label htmlFor="filter-entity-type">Entity Type</label>
              <select
                id="filter-entity-type"
                value={localEntityType}
                onChange={(e) => {
                  setLocalEntityType(e.target.value)
                  updateFilter('entityType', e.target.value as any || undefined)
                }}
              >
                <option value="">All Types</option>
                <option value="error">Error</option>
                <option value="url">URL</option>
                <option value="tool_id">Tool ID</option>
                <option value="decision">Decision</option>
                <option value="code_ref">Code Reference</option>
              </select>
            </div>

            {/* Entity Value Filter */}
            <div className="filter-field">
              <label htmlFor="filter-entity-value">Entity Value</label>
              <input
                id="filter-entity-value"
                type="text"
                placeholder="e.g., ConnectionTimeout"
                value={localEntityValue}
                onChange={(e) => {
                  setLocalEntityValue(e.target.value)
                  updateFilter('entityValue', e.target.value || undefined)
                }}
              />
            </div>

            {/* Created After Filter */}
            <div className="filter-field">
              <label htmlFor="filter-created-after">Created After</label>
              <input
                id="filter-created-after"
                type="datetime-local"
                value={localCreatedAfter}
                onChange={(e) => {
                  setLocalCreatedAfter(e.target.value)
                  updateFilter('createdAfter', e.target.value || undefined)
                }}
              />
            </div>

            {/* Created Before Filter */}
            <div className="filter-field">
              <label htmlFor="filter-created-before">Created Before</label>
              <input
                id="filter-created-before"
                type="datetime-local"
                value={localCreatedBefore}
                onChange={(e) => {
                  setLocalCreatedBefore(e.target.value)
                  updateFilter('createdBefore', e.target.value || undefined)
                }}
              />
            </div>
          </div>

          {activeFilterCount > 0 && (
            <div className="filter-actions">
              <button className="clear-filters-btn" onClick={handleClearFilters}>
                Clear All Filters
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
