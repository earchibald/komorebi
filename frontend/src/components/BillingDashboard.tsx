/**
 * BillingDashboard — LLM usage table + budget controls
 *
 * Shows per-model token counts, cost estimates, and allows
 * setting a daily budget cap with auto-downgrade toggle.
 */

import { useEffect, useState } from 'react'
import {
  llmUsage,
  budgetConfig,
  budgetLoading,
  totalCost,
  isThrottled,
  fetchUsage,
  fetchBudget,
  updateBudget,
  type BudgetConfig,
} from '../store/oracle'

export function BillingDashboard() {
  const [editing, setEditing] = useState(false)
  const [capInput, setCapInput] = useState('')
  const [autoDowngrade, setAutoDowngrade] = useState(true)
  const [downgradeModel, setDowngradeModel] = useState('llama3')

  useEffect(() => {
    fetchUsage()
    fetchBudget()
  }, [])

  useEffect(() => {
    if (budgetConfig.value) {
      setCapInput(budgetConfig.value.daily_cap_usd?.toString() ?? '')
      setAutoDowngrade(budgetConfig.value.auto_downgrade)
      setDowngradeModel(budgetConfig.value.downgrade_model)
    }
  }, [budgetConfig.value])

  const handleSaveBudget = async () => {
    const config: BudgetConfig = {
      daily_cap_usd: capInput ? parseFloat(capInput) : null,
      auto_downgrade: autoDowngrade,
      downgrade_model: downgradeModel,
    }
    await updateBudget(config)
    setEditing(false)
  }

  return (
    <div className="billing-dashboard">
      <h2>💰 LLM Cost Dashboard</h2>

      {isThrottled.value && (
        <div className="throttle-alert" style={{
          background: 'var(--error-bg, #fee)',
          border: '1px solid var(--error-border, #c00)',
          padding: '12px',
          borderRadius: '8px',
          marginBottom: '16px',
        }}>
          ⚠️ <strong>Budget cap reached.</strong>{' '}
          {budgetConfig.value?.auto_downgrade
            ? `Auto-downgraded to ${budgetConfig.value.downgrade_model}`
            : 'Requests blocked until budget is increased.'}
        </div>
      )}

      {/* Usage Table */}
      <div className="usage-table" style={{ marginBottom: '24px' }}>
        <h3>Usage This Period</h3>
        {budgetLoading.value ? (
          <p>Loading...</p>
        ) : llmUsage.value.length === 0 ? (
          <p style={{ color: 'var(--text-muted)' }}>No LLM usage recorded yet.</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border)' }}>
                <th style={{ textAlign: 'left', padding: '8px' }}>Model</th>
                <th style={{ textAlign: 'right', padding: '8px' }}>Input</th>
                <th style={{ textAlign: 'right', padding: '8px' }}>Output</th>
                <th style={{ textAlign: 'right', padding: '8px' }}>Total</th>
                <th style={{ textAlign: 'right', padding: '8px' }}>Requests</th>
                <th style={{ textAlign: 'right', padding: '8px' }}>Cost</th>
              </tr>
            </thead>
            <tbody>
              {llmUsage.value.map((m) => (
                <tr key={m.model_name} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '8px', fontFamily: 'monospace' }}>{m.model_name}</td>
                  <td style={{ textAlign: 'right', padding: '8px' }}>{m.input_tokens.toLocaleString()}</td>
                  <td style={{ textAlign: 'right', padding: '8px' }}>{m.output_tokens.toLocaleString()}</td>
                  <td style={{ textAlign: 'right', padding: '8px' }}>{m.total_tokens.toLocaleString()}</td>
                  <td style={{ textAlign: 'right', padding: '8px' }}>{m.request_count}</td>
                  <td style={{ textAlign: 'right', padding: '8px' }}>
                    ${m.estimated_cost_usd.toFixed(4)}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr style={{ fontWeight: 'bold', borderTop: '2px solid var(--border)' }}>
                <td style={{ padding: '8px' }}>Total</td>
                <td colSpan={4}></td>
                <td style={{ textAlign: 'right', padding: '8px' }}>
                  ${totalCost.value.toFixed(4)}
                </td>
              </tr>
            </tfoot>
          </table>
        )}
      </div>

      {/* Budget Controls */}
      <div className="budget-controls" style={{
        background: 'var(--card-bg, #f8f8f8)',
        padding: '16px',
        borderRadius: '8px',
      }}>
        <h3>Budget Configuration</h3>
        {!editing ? (
          <div>
            <p>
              <strong>Daily Cap:</strong>{' '}
              {budgetConfig.value?.daily_cap_usd
                ? `$${budgetConfig.value.daily_cap_usd.toFixed(2)}`
                : 'No limit'}
            </p>
            <p>
              <strong>Auto-Downgrade:</strong>{' '}
              {budgetConfig.value?.auto_downgrade ? 'Enabled' : 'Disabled'}
              {budgetConfig.value?.auto_downgrade && (
                <> → {budgetConfig.value.downgrade_model}</>
              )}
            </p>
            <button onClick={() => setEditing(true)} style={{ marginTop: '8px' }}>
              Edit Budget
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <label>
              Daily Cap (USD):
              <input
                type="number"
                step="0.01"
                min="0"
                value={capInput}
                onChange={(e) => setCapInput(e.target.value)}
                placeholder="No limit"
                style={{ marginLeft: '8px', width: '120px' }}
              />
            </label>
            <label>
              <input
                type="checkbox"
                checked={autoDowngrade}
                onChange={(e) => setAutoDowngrade(e.target.checked)}
              />{' '}
              Auto-downgrade to local model when cap is reached
            </label>
            <label>
              Downgrade model:
              <input
                type="text"
                value={downgradeModel}
                onChange={(e) => setDowngradeModel(e.target.value)}
                style={{ marginLeft: '8px', width: '120px' }}
              />
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button onClick={handleSaveBudget}>Save</button>
              <button onClick={() => setEditing(false)}>Cancel</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
