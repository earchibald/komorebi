/**
 * StagingArea - Target selector and dispatcher UI
 * 
 * Allows users to:
 * 1. Select a delivery target from available targets
 * 2. Fill in the dynamic form for that target
 * 3. Dispatch the data to the target via MCP
 * 4. View dispatch results
 */

import { useEffect, useState } from 'react'
import { DynamicForm } from './DynamicForm'
import {
  availableTargets,
  selectedTarget,
  selectTarget,
  canDispatch,
  dispatchToTarget,
  dispatchLoading,
  dispatchError,
  lastDispatchResult,
  schemasLoading,
  schemasError,
  initializeTargetStore
} from '../store/targets'

export function StagingArea() {
  const [isDispatching, setIsDispatching] = useState(false)
  
  // Initialize store on mount
  useEffect(() => {
    initializeTargetStore()
  }, [])
  
  const handleTargetSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const targetName = e.target.value || null
    selectTarget(targetName)
  }
  
  const handleDispatch = async () => {
    if (!canDispatch.value) return
    
    setIsDispatching(true)
    try {
      await dispatchToTarget()
      // Success! lastDispatchResult will be set by the action
    } catch (error) {
      // Error is already set in dispatchError by the action
      console.error('Dispatch failed:', error)
    } finally {
      setIsDispatching(false)
    }
  }
  
  // Read signal values outside JSX
  const targets = availableTargets.value
  const selected = selectedTarget.value
  const canSend = canDispatch.value
  const isLoading = dispatchLoading.value || isDispatching
  const error = dispatchError.value
  const result = lastDispatchResult.value
  const loading = schemasLoading.value
  const loadError = schemasError.value
  
  return (
    <div className="staging-area">
      <div className="staging-header">
        <h2>📤 Dispatch to External Tools</h2>
        <p className="staging-description">
          Send data to external systems via MCP (GitHub, Jira, Slack, etc.)
        </p>
      </div>
      
      {/* Loading / Error States */}
      {loading && (
        <div className="staging-loading">
          <span className="spinner">⏳</span> Loading delivery targets...
        </div>
      )}
      
      {loadError && (
        <div className="staging-error">
          <strong>Failed to load targets:</strong> {loadError}
        </div>
      )}
      
      {/* Target Selector */}
      {!loading && !loadError && targets.length > 0 && (
        <div className="target-selector">
          <label htmlFor="target-select" className="selector-label">
            Select Delivery Target:
          </label>
          <select
            id="target-select"
            className="target-select"
            value={selected || ''}
            onChange={handleTargetSelect}
          >
            <option value="">-- Choose a target --</option>
            {targets.map((target) => (
              <option key={target.name} value={target.name}>
                {target.icon && `${target.icon} `}{target.display_name}
              </option>
            ))}
          </select>
        </div>
      )}
      
      {/* No targets available */}
      {!loading && !loadError && targets.length === 0 && (
        <div className="staging-empty">
          <p>No delivery targets are available.</p>
          <p className="staging-hint">
            Check that MCP servers are configured and running.
          </p>
        </div>
      )}
      
      {/* Dynamic Form (based on selected target) */}
      {selected && <DynamicForm />}
      
      {/* Dispatch Button */}
      {selected && (
        <div className="dispatch-actions">
          <button
            className="dispatch-button"
            onClick={handleDispatch}
            disabled={!canSend || isLoading}
          >
            {isLoading ? '⏳ Dispatching...' : '🚀 Dispatch'}
          </button>
          
          {!canSend && !isLoading && (
            <p className="dispatch-hint">
              Fill in all required fields before dispatching
            </p>
          )}
        </div>
      )}
      
      {/* Dispatch Error */}
      {error && (
        <div className="dispatch-error">
          <strong>Dispatch failed:</strong> {error}
        </div>
      )}
      
      {/* Dispatch Success */}
      {result && result.success && (
        <div className="dispatch-success">
          <h3>✅ Dispatched successfully!</h3>
          <div className="dispatch-result-details">
            <p><strong>Target:</strong> {result.target_name}</p>
            <p><strong>Tool:</strong> {result.mcp_tool}</p>
            {result.result && (
              <details className="dispatch-result-data">
                <summary>View Result Data</summary>
                <pre>{JSON.stringify(result.result, null, 2)}</pre>
              </details>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
