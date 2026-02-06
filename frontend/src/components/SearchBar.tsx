/**
 * SearchBar - Text search input with debouncing and result count
 */

import { searchQuery, searchResults, searchLoading, debouncedSearch, clearSearch, isSearchActive } from '../store'

export function SearchBar() {
  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    searchQuery.value = e.target.value
    debouncedSearch()
  }

  const handleClear = () => {
    clearSearch()
  }

  return (
    <div className="search-bar">
      <div className="search-input-wrapper">
        <span className="search-icon">🔍</span>
        <input
          type="text"
          className="search-input"
          placeholder="Search chunks by content..."
          value={searchQuery.value}
          onChange={handleInput}
          autoComplete="off"
        />
        {isSearchActive.value && (
          <button 
            className="search-clear" 
            onClick={handleClear}
            aria-label="Clear search"
          >
            ✕
          </button>
        )}
      </div>
      
      {searchLoading.value && (
        <div className="search-status loading">
          <span className="spinner">⏳</span> Searching...
        </div>
      )}
      
      {searchResults.value && !searchLoading.value && (
        <div className="search-status results">
          <span className="result-count">
            {searchResults.value.total} result{searchResults.value.total !== 1 ? 's' : ''}
          </span>
          {searchResults.value.query && (
            <span className="result-query">
              for "{searchResults.value.query}"
            </span>
          )}
        </div>
      )}
    </div>
  )
}
