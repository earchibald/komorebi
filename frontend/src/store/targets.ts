/**
 * Target Delivery System Store - State management for target delivery
 * 
 * Manages:
 * - Available target schemas fetched from backend
 * - Selected target
 * - Form data (reactive updates from DynamicForm)
 * - Context data (repo owner, repo name, etc.)
 */

import { signal, computed } from '@preact/signals-react'

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

export type FieldType = 'text' | 'textarea' | 'markdown' | 'tags' | 'select' | 'checkbox'

export interface FieldSchema {
  name: string
  type: FieldType
  label: string
  placeholder?: string
  required: boolean
  options?: string[]
  default?: any
  help_text?: string
}

export interface TargetSchema {
  name: string
  display_name: string
  description: string
  icon?: string
  fields: FieldSchema[]
  schema_version: string
}

export interface DispatchRequest {
  target_name: string
  data: Record<string, any>
  context: Record<string, any>
}

export interface DispatchResponse {
  success: boolean
  target_name: string
  mcp_tool: string
  result?: Record<string, any>
  error?: string
}

// ─────────────────────────────────────────────────────────────
//Signals
// ─────────────────────────────────────────────────────────────

/** All available target schemas loaded from backend */
export const availableTargets = signal<TargetSchema[]>([])

/** Currently selected target name (null if none selected) */
export const selectedTarget = signal<string | null>(null)

/** Form data for the selected target (keys = field names) */
export const formData = signal<Record<string, any>>({})

/** Context data (repo owner, repo name, workspace, etc.) */
export const contextData = signal<Record<string, any>>({
  repo_owner: 'earchibald',  // Default values from current repo
  repo_name: 'komorebi'
})

/** Loading state for schema fetch */
export const schemasLoading = signal<boolean>(false)

/** Error state for schema fetch */
export const schemasError = signal<string | null>(null)

/** Loading state for dispatch */
export const dispatchLoading = signal<boolean>(false)

/** Error state for dispatch */
export const dispatchError = signal<string | null>(null)

/** Last dispatch result */
export const lastDispatchResult = signal<DispatchResponse | null>(null)

// ─────────────────────────────────────────────────────────────
// Computed Values
// ─────────────────────────────────────────────────────────────

/** Get the schema for the currently selected target */
export const currentTargetSchema = computed<TargetSchema | null>(() => {
  const targetName = selectedTarget.value
  if (!targetName) return null
  
  return availableTargets.value.find(t => t.name === targetName) ?? null
})

/** Check if form is valid (all required fields filled) */
export const isFormValid = computed<boolean>(() => {
  const schema = currentTargetSchema.value
  if (!schema) return false
  
  const data = formData.value
  
  // Check all required fields
  for (const field of schema.fields) {
    if (field.required) {
      const value = data[field.name]
      if (value === undefined || value === null || value === '') {
        return false
      }
    }
  }
  
  return true
})

/** Check if dispatch is ready (target selected, form valid, not loading) */
export const canDispatch = computed<boolean>(() => {
  return !!(
    selectedTarget.value &&
    isFormValid.value &&
    !dispatchLoading.value
  )
})

// ─────────────────────────────────────────────────────────────
// Actions
// ─────────────────────────────────────────────────────────────

/**
 * Fetch available target schemas from backend
 */
export async function fetchTargetSchemas(): Promise<void> {
  schemasLoading.value = true
  schemasError.value = null
  
  try {
    const response = await fetch('http://localhost:8000/api/v1/targets/schemas')
    
    if (!response.ok) {
      throw new Error(`Failed to fetch schemas: ${response.statusText}`)
    }
    
    const data = await response.json()
    availableTargets.value = data.schemas
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error'
    schemasError.value = message
    console.error('Failed to fetch target schemas:', error)
  } finally {
    schemasLoading.value = false
  }
}

/**
 * Select a target by name
 * Resets form data when target changes
 */
export function selectTarget(targetName: string | null): void {
  selectedTarget.value = targetName
  formData.value = {}
  dispatchError.value = null
  lastDispatchResult.value = null
}

/**
 * Update a single form field
 */
export function updateFormField(fieldName: string, value: any): void {
  formData.value = {
    ...formData.value,
    [fieldName]: value
  }
}

/**
 * Update multiple form fields at once
 */
export function updateFormData(data: Record<string, any>): void {
  formData.value = {
    ...formData.value,
    ...data
  }
}

/**
 * Update context data
 */
export function updateContext(context: Record<string, any>): void {
  contextData.value = {
    ...contextData.value,
    ...context
  }
}

/**
 * Reset form data
 */
export function resetForm(): void {
  formData.value = {}
  dispatchError.value = null
  lastDispatchResult.value = null
}

/**
 * Dispatch current form data to selected target via MCP
 */
export async function dispatchToTarget(): Promise<DispatchResponse> {
  if (!canDispatch.value) {
    throw new Error('Cannot dispatch: form is invalid or no target selected')
  }
  
  dispatchLoading.value = true
  dispatchError.value = null
  
  try {
    const request: DispatchRequest = {
      target_name: selectedTarget.value!,
      data: formData.value,
      context: contextData.value
    }
    
    const response = await fetch('http://localhost:8000/api/v1/dispatch', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(request)
    })
    
    const result: DispatchResponse = await response.json()
    
    if (!response.ok) {
      throw new Error(result.error || `Dispatch failed: ${response.statusText}`)
    }
    
    lastDispatchResult.value = result
    
    // Reset form on success
    resetForm()
    
    return result
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error'
    dispatchError.value = message
    console.error('Failed to dispatch:', error)
    throw error
  } finally {
    dispatchLoading.value = false
  }
}

/**
 * Initialize the store (call this on app mount)
 */
export async function initializeTargetStore(): Promise<void> {
  await fetchTargetSchemas()
}
