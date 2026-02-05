/**
 * Komorebi Store - State management using Preact signals
 * 
 * Signals provide fine-grained reactivity without the
 * overhead of context providers or reducers.
 */

import { signal, computed } from '@preact/signals-react'

// Types
export interface Chunk {
  id: string
  content: string
  summary: string | null
  project_id: string | null
  tags: string[]
  status: 'inbox' | 'processed' | 'compacted' | 'archived'
  source: string | null
  token_count: number | null
  created_at: string
  updated_at: string
}

export interface Project {
  id: string
  name: string
  description: string | null
  context_summary: string | null
  chunk_count: number
  created_at: string
  updated_at: string
}

export interface ChunkStats {
  inbox: number
  processed: number
  compacted: number
  archived: number
  total: number
}

// API base URL
const API_URL = '/api/v1'

// Signals (reactive state)
export const chunks = signal<Chunk[]>([])
export const projects = signal<Project[]>([])
export const stats = signal<ChunkStats>({
  inbox: 0,
  processed: 0,
  compacted: 0,
  archived: 0,
  total: 0,
})
export const loading = signal(false)
export const error = signal<string | null>(null)

// Computed values
export const inboxChunks = computed(() => 
  chunks.value.filter(c => c.status === 'inbox')
)

export const processedChunks = computed(() =>
  chunks.value.filter(c => c.status === 'processed')
)

// Actions
export async function fetchChunks(status?: string, limit = 100) {
  loading.value = true
  error.value = null
  
  try {
    const params = new URLSearchParams()
    if (status) params.set('status', status)
    params.set('limit', String(limit))
    
    const response = await fetch(`${API_URL}/chunks?${params}`)
    if (!response.ok) throw new Error('Failed to fetch chunks')
    
    chunks.value = await response.json()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Unknown error'
  } finally {
    loading.value = false
  }
}

export async function fetchStats() {
  try {
    const response = await fetch(`${API_URL}/chunks/stats`)
    if (!response.ok) throw new Error('Failed to fetch stats')
    
    stats.value = await response.json()
  } catch (e) {
    console.error('Failed to fetch stats:', e)
  }
}

export async function captureChunk(content: string, tags: string[] = []) {
  loading.value = true
  error.value = null
  
  try {
    const response = await fetch(`${API_URL}/chunks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content,
        tags,
        source: 'dashboard',
      }),
    })
    
    if (!response.ok) throw new Error('Failed to capture chunk')
    
    const newChunk = await response.json()
    chunks.value = [newChunk, ...chunks.value]
    
    // Refresh stats
    await fetchStats()
    
    return newChunk
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Unknown error'
    throw e
  } finally {
    loading.value = false
  }
}

export async function fetchProjects() {
  loading.value = true
  error.value = null
  
  try {
    const response = await fetch(`${API_URL}/projects`)
    if (!response.ok) throw new Error('Failed to fetch projects')
    
    projects.value = await response.json()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Unknown error'
  } finally {
    loading.value = false
  }
}

export async function createProject(name: string, description?: string) {
  loading.value = true
  error.value = null
  
  try {
    const response = await fetch(`${API_URL}/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description }),
    })
    
    if (!response.ok) throw new Error('Failed to create project')
    
    const newProject = await response.json()
    projects.value = [newProject, ...projects.value]
    
    return newProject
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Unknown error'
    throw e
  } finally {
    loading.value = false
  }
}

// SSE connection for real-time updates
let eventSource: EventSource | null = null

export function connectSSE() {
  if (eventSource) return
  
  eventSource = new EventSource(`${API_URL}/sse/events`)
  
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      handleSSEEvent(data)
    } catch (e) {
      console.error('Failed to parse SSE event:', e)
    }
  }
  
  eventSource.onerror = () => {
    console.error('SSE connection error, reconnecting...')
    disconnectSSE()
    setTimeout(connectSSE, 5000)
  }
}

export function disconnectSSE() {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
}

function handleSSEEvent(event: { type: string; chunk_id: string; data: Record<string, unknown> }) {
  switch (event.type) {
    case 'chunk.created':
      // Chunk already added during capture, but refresh just in case
      fetchStats()
      break
    case 'chunk.updated':
      // Update the chunk in the list
      chunks.value = chunks.value.map(c =>
        c.id === event.chunk_id ? { ...c, ...event.data } as Chunk : c
      )
      fetchStats()
      break
    case 'chunk.deleted':
      chunks.value = chunks.value.filter(c => c.id !== event.chunk_id)
      fetchStats()
      break
    default:
      // Other events
      break
  }
}
