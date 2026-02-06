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

export interface Entity {
  id: number
  chunk_id: string
  project_id: string
  entity_type: 'error' | 'url' | 'tool_id' | 'decision' | 'code_ref'
  value: string
  confidence: number
  context_snippet: string | null
  created_at: string
}

// API base URL
const API_URL = '/api/v1'

const STORAGE_PREFIX = 'komorebi-dashboard'
const STORAGE_KEYS = {
  chunks: `${STORAGE_PREFIX}:chunks`,
  projects: `${STORAGE_PREFIX}:projects`,
  stats: `${STORAGE_PREFIX}:stats`,
}

function readCache<T>(key: string): T | null {
  if (typeof window === 'undefined') return null

  try {
    const raw = window.localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : null
  } catch {
    return null
  }
}

function writeCache<T>(key: string, value: T): void {
  if (typeof window === 'undefined') return

  try {
    window.localStorage.setItem(key, JSON.stringify(value))
    console.log(`💾 Cached data to ${key.split(':')[1]}`)
  } catch {
    // Ignore storage failures (quota, private mode, etc.)
  }
}

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

// Debounce tracking
let fetchChunksPromise: Promise<void> | null = null
let fetchStatsPromise: Promise<void> | null = null
let fetchProjectsPromise: Promise<void> | null = null

// Computed values
export const inboxChunks = computed(() => 
  chunks.value.filter(c => c.status === 'inbox')
)

export const processedChunks = computed(() =>
  chunks.value.filter(c => c.status === 'processed')
)

// Drawer state
export const selectedChunk = signal<Chunk | null>(null)
export const chunkEntities = signal<Entity[]>([])
export const entitiesLoading = signal(false)

const cachedChunks = readCache<Chunk[]>(STORAGE_KEYS.chunks)
const cachedProjects = readCache<Project[]>(STORAGE_KEYS.projects)
const cachedStats = readCache<ChunkStats>(STORAGE_KEYS.stats)

if (cachedChunks) {
  console.log(`📦 Loaded ${cachedChunks.length} chunks from cache`)
  chunks.value = cachedChunks
}
if (cachedProjects) {
  console.log(`📁 Loaded ${cachedProjects.length} projects from cache`)
  projects.value = cachedProjects
}
if (cachedStats) {
  console.log(`📊 Loaded stats from cache:`, cachedStats)
  stats.value = cachedStats
}

// Actions
export async function fetchChunks(status?: string, limit = 100) {
  // NOTE: New pattern (Feb 2026) - Fetch-All-Filter-Client
  // Components should call fetchChunks(undefined, 500) to get all chunks,
  // then filter client-side for instant tab switching.
  // Only pass a status filter if you specifically need server-side filtering.
  
  // Debounce: return existing promise if fetch is in progress
  if (fetchChunksPromise) return fetchChunksPromise
  
  loading.value = true
  error.value = null
  
  fetchChunksPromise = (async () => {
    try {
      const params = new URLSearchParams()
      if (status) params.set('status', status)
      params.set('limit', String(limit))
      
      const response = await fetch(`${API_URL}/chunks?${params}`)
      if (!response.ok) throw new Error('Failed to fetch chunks')
      
      chunks.value = await response.json()
      writeCache(STORAGE_KEYS.chunks, chunks.value)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
    } finally {
      loading.value = false
      fetchChunksPromise = null
    }
  })()
  
  return fetchChunksPromise
}

export async function fetchStats() {
  // Debounce: return existing promise if fetch is in progress
  if (fetchStatsPromise) return fetchStatsPromise
  
  fetchStatsPromise = (async () => {
    try {
      const response = await fetch(`${API_URL}/chunks/stats`)
      if (!response.ok) throw new Error('Failed to fetch stats')
      
      stats.value = await response.json()
      writeCache(STORAGE_KEYS.stats, stats.value)
    } catch (e) {
      console.error('Failed to fetch stats:', e)
    } finally {
      fetchStatsPromise = null
    }
  })()
  
  return fetchStatsPromise
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
    writeCache(STORAGE_KEYS.chunks, chunks.value)
    
    // Stats will be refreshed via SSE event
    
    return newChunk
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Unknown error'
    throw e
  } finally {
    loading.value = false
  }
}

export async function fetchProjects() {
  // Debounce: return existing promise if fetch is in progress
  if (fetchProjectsPromise) return fetchProjectsPromise
  
  loading.value = true
  error.value = null
  
  fetchProjectsPromise = (async () => {
    try {
      const response = await fetch(`${API_URL}/projects`)
      if (!response.ok) throw new Error('Failed to fetch projects')
      
      projects.value = await response.json()
      writeCache(STORAGE_KEYS.projects, projects.value)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
    } finally {
      loading.value = false
      fetchProjectsPromise = null
    }
  })()
  
  return fetchProjectsPromise
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
    writeCache(STORAGE_KEYS.projects, projects.value)
    
    return newProject
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Unknown error'
    throw e
  } finally {
    loading.value = false
  }
}

// Drawer actions
export function selectChunk(chunk: Chunk): void {
  selectedChunk.value = chunk
  chunkEntities.value = []
  fetchChunkEntities(chunk.id)
}

export function closeDrawer(): void {
  selectedChunk.value = null
  chunkEntities.value = []
  entitiesLoading.value = false
}

export async function fetchChunkEntities(chunkId: string): Promise<void> {
  entitiesLoading.value = true
  try {
    const response = await fetch(`${API_URL}/entities/chunks/${chunkId}`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    chunkEntities.value = await response.json()
  } catch (e) {
    console.error('Failed to fetch chunk entities:', e)
    chunkEntities.value = []
  } finally {
    entitiesLoading.value = false
  }
}

// SSE connection for real-time updates
let eventSource: EventSource | null = null

export function connectSSE() {
  if (eventSource) return
  
  console.log('🔌 Connecting to SSE...')
  eventSource = new EventSource(`${API_URL}/sse/events`)
  
  eventSource.onopen = () => {
    console.log('✅ SSE connected')
  }
  
  eventSource.onmessage = (event) => {
    console.log('📨 SSE raw event:', event)
    try {
      if (!event.data || event.data.trim() === '') return
      const data = JSON.parse(event.data)
      console.log('📨 SSE parsed data:', data)
      handleSSEEvent(data)
    } catch (e) {
      console.error('Failed to parse SSE event:', e, 'Raw data:', event.data)
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

// Debounced stats refresh to avoid hammering the API
let statsRefreshTimeout: number | null = null
function scheduleStatsRefresh() {
  if (statsRefreshTimeout) return // Already scheduled
  statsRefreshTimeout = window.setTimeout(() => {
    fetchStats()
    statsRefreshTimeout = null
  }, 500)
}

function handleSSEEvent(event: { type: string; chunk_id: string; data: Record<string, unknown> }) {
  console.log('📡 SSE event:', event.type)
  
  switch (event.type) {
    case 'chunk.created':
      // Refetch chunks to show the new one
      fetchChunks()
      scheduleStatsRefresh()
      break
    case 'chunk.updated':
      // Update the chunk in the list
      chunks.value = chunks.value.map(c =>
        c.id === event.chunk_id ? { ...c, ...event.data } as Chunk : c
      )
      writeCache(STORAGE_KEYS.chunks, chunks.value)
      scheduleStatsRefresh()
      break
    case 'chunk.deleted':
      chunks.value = chunks.value.filter(c => c.id !== event.chunk_id)
      writeCache(STORAGE_KEYS.chunks, chunks.value)
      scheduleStatsRefresh()
      break
    case 'mcp.status_changed':
      // MCP server status update – emit a custom event for MCPPanel to pick up
      console.log('🔌 MCP status changed:', event.data)
      window.dispatchEvent(new CustomEvent('mcp:status_changed', { detail: event.data }))
      break
    default:
      // Other events
      break
  }
}
