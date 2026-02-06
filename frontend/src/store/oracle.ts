/**
 * Oracle Store — Signals for Context Oracle features
 *
 * Manages reactive state for:
 * - LLM usage & budget (BillingDashboard)
 * - Traces (context sessions)
 * - File events (WatcherStatus)
 */

import { signal, computed } from '@preact/signals-react'

// ── Types ──────────────────────────────────────────────────

export interface ModelUsage {
  model_name: string
  input_tokens: number
  output_tokens: number
  total_tokens: number
  estimated_cost_usd: number
  request_count: number
}

export interface UsageSummary {
  models: ModelUsage[]
  total_cost_usd: number
  budget_cap_usd: number | null
  budget_remaining_usd: number | null
  throttled: boolean
  period: string
}

export interface BudgetConfig {
  daily_cap_usd: number | null
  auto_downgrade: boolean
  downgrade_model: string
}

export interface TraceSummary {
  id: string
  name: string
  status: 'active' | 'paused' | 'closed'
  meta_summary: string | null
  chunk_count: number
  last_activity: string | null
}

export interface FileEvent {
  id: string
  trace_id: string
  path: string
  crud_op: 'created' | 'modified' | 'deleted' | 'moved'
  size_bytes: number | null
  hash_prefix: string | null
  mime_type: string | null
  created_at: string
}

export interface WatcherInfo {
  path: string
  recursive: boolean
  pid: number
}

// ── Signals ────────────────────────────────────────────────

// LLM Usage
export const llmUsage = signal<ModelUsage[]>([])
export const budgetConfig = signal<BudgetConfig | null>(null)
export const budgetLoading = signal(false)

// Traces
export const activeTrace = signal<TraceSummary | null>(null)
export const traces = signal<TraceSummary[]>([])

// File Events
export const recentFileEvents = signal<FileEvent[]>([])
export const activeWatchers = signal<WatcherInfo[]>([])

// ── Derived ────────────────────────────────────────────────

export const totalCost = computed(() =>
  llmUsage.value.reduce((sum, m) => sum + m.estimated_cost_usd, 0)
)

export const isThrottled = computed(() => {
  if (!budgetConfig.value?.daily_cap_usd) return false
  return totalCost.value >= budgetConfig.value.daily_cap_usd
})

// ── API helpers ────────────────────────────────────────────

const API_BASE = '/api/v1'

export async function fetchUsage(): Promise<void> {
  budgetLoading.value = true
  try {
    const resp = await fetch(`${API_BASE}/llm/usage`)
    if (resp.ok) {
      const data: UsageSummary = await resp.json()
      llmUsage.value = data.models
      budgetConfig.value = {
        daily_cap_usd: data.budget_cap_usd,
        auto_downgrade: true,
        downgrade_model: 'llama3',
      }
    }
  } finally {
    budgetLoading.value = false
  }
}

export async function fetchBudget(): Promise<void> {
  const resp = await fetch(`${API_BASE}/llm/budget`)
  if (resp.ok) {
    budgetConfig.value = await resp.json()
  }
}

export async function updateBudget(config: BudgetConfig): Promise<void> {
  const resp = await fetch(`${API_BASE}/llm/budget`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  if (resp.ok) {
    budgetConfig.value = await resp.json()
  }
}

export async function fetchActiveTrace(): Promise<void> {
  const resp = await fetch(`${API_BASE}/traces/active`)
  if (resp.ok) {
    activeTrace.value = await resp.json()
  }
}

export async function fetchTraces(): Promise<void> {
  const resp = await fetch(`${API_BASE}/traces`)
  if (resp.ok) {
    traces.value = await resp.json()
  }
}

export async function fetchFileEvents(traceId?: string): Promise<void> {
  const params = traceId ? `?trace_id=${traceId}&limit=50` : '?limit=50'
  const resp = await fetch(`${API_BASE}/file-events${params}`)
  if (resp.ok) {
    recentFileEvents.value = await resp.json()
  }
}
