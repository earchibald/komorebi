/**
 * SearchBar - Text search input with debouncing and result count
 * 
 * Uses local React state bridge to avoid signal/React controlled input race condition.
 * Signal values are read outside JSX to prevent @preact/signals-react v2 reactive binding issues.
 */

import { useState, useEffect } from 'react'
import { searchQuery, searchResults, searchLoading, debouncedSearch, clearSearch, isSearchActive } from '../store'

export function SearchBar() {
  const [localQuery, setLocalQuery] = useState(searchQuery.value)

  // Sync signal → local when signal changes externally (e.g., clearSearch)
  useEffect(() => {
    setLocalQuery(searchQuery.value)
  }, [searchQuery.value])

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value
    setLocalQuery(val)
    searchQuery.value = val
    debouncedSearch()
  }

  const handleClear = () => {
    clearSearch()
    setLocalQuery('')
  }

  // Read signal values outside JSX to avoid reactive binding issues
  const isActive = isSearchActive.value
  const isLoading = searchLoading.value
  const results = searchResults.value

  return (
    <div className="search-bar">
      <div className="search-input-wrapper">
        <span className="search-icon">🔍</span>
        <input
          type="text"
          className="search-input"
          placeholder="Search chunks by content..."
          value={localQuery}
          onChange={handleInput}
          autoComplete="off"
        />
        {isActive && (
          <button 
            className="search-clear" 
            onClick={handleClear}
            aria-label="Clear search"
          >
            ✕
          </button>
        )}
      </div>
      
      {isLoading && (
        <div className="search-status loading">
          <span className="spinner">⏳</span> Searching...
        </div>
      )}
      
      {results && !isLoading && (
        <div className="search-status results">
          <span className="result-count">
            {results.total} result{results.total !== 1 ? 's' : ''}
          </span>
          {results.query && (
            <span className="result-query">
              for "{results.query}"
            </span>
          )}
        </div>
      )}
    </div>
  )
}
