/**
 * DynamicForm - Schema-driven form renderer for target delivery
 * 
 * Renders form fields dynamically based on TargetSchema from backend.
 * Supports: text, textarea, markdown, tags, select, checkbox field types.
 * 
 * Uses local React state to avoid signal/React controlled input race conditions.
 * Syncs with store signals on mount and form submission.
 */

import { useState, useEffect } from 'react'
import { currentTargetSchema, formData, updateFormField, type FieldSchema, type FieldType } from '../store/targets'

export function DynamicForm() {
  const schema = currentTargetSchema.value
  
  // Local state for form inputs (avoids signal race conditions)
  const [localFormData, setLocalFormData] = useState<Record<string, any>>({})
  
  // Sync store → local on schema or formData change
  useEffect(() => {
    setLocalFormData(formData.value)
  }, [formData.value, schema])
  
  if (!schema) {
    return (
      <div className="dynamic-form-empty">
        <p>Select a target to configure delivery options</p>
      </div>
    )
  }
  
  const handleFieldChange = (fieldName: string, value: any) => {
    // Update local state immediately
    const newData = { ...localFormData, [fieldName]: value }
    setLocalFormData(newData)
    
    // Update signal store (for validation and dispatch)
    updateFormField(fieldName, value)
  }
  
  return (
    <div className="dynamic-form">
      <div className="form-header">
        <h3>
          {schema.icon && <span className="target-icon">{schema.icon}</span>}
          {schema.display_name}
        </h3>
        <p className="form-description">{schema.description}</p>
      </div>
      
      <div className="form-fields">
        {schema.fields.map((field) => (
          <FormField
            key={field.name}
            field={field}
            value={localFormData[field.name]}
            onChange={(value) => handleFieldChange(field.name, value)}
          />
        ))}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// Individual Field Renderer
// ─────────────────────────────────────────────────────────────

interface FormFieldProps {
  field: FieldSchema
  value: any
  onChange: (value: any) => void
}

function FormField({ field, value, onChange }: FormFieldProps) {
  const fieldValue = value ?? field.default ?? ''
  
  return (
    <div className={`form-field form-field-${field.type}`}>
      <label htmlFor={field.name} className="field-label">
        {field.label}
        {field.required && <span className="required-indicator">*</span>}
      </label>
      
      {renderFieldInput(field, fieldValue, onChange)}
      
      {field.help_text && (
        <p className="field-help-text">{field.help_text}</p>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────
// Field Type Renderers
// ─────────────────────────────────────────────────────────────

function renderFieldInput(
  field: FieldSchema,
  value: any,
  onChange: (value: any) => void
): JSX.Element {
  const commonProps = {
    id: field.name,
    name: field.name,
    required: field.required,
    placeholder: field.placeholder || ''
  }
  
  switch (field.type) {
    case 'text':
      return (
        <input
          {...commonProps}
          type="text"
          className="field-input field-input-text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      )
    
    case 'textarea':
      return (
        <textarea
          {...commonProps}
          className="field-input field-input-textarea"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={4}
        />
      )
    
    case 'markdown':
      return (
        <textarea
          {...commonProps}
          className="field-input field-input-markdown"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={8}
          spellCheck={true}
        />
      )
    
    case 'tags':
      return (
        <input
          {...commonProps}
          type="text"
          className="field-input field-input-tags"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={field.placeholder || 'Comma-separated tags'}
        />
      )
    
    case 'select':
      return (
        <select
          {...commonProps}
          className="field-input field-input-select"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        >
          <option value="">Select an option...</option>
          {field.options?.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      )
    
    case 'checkbox':
      return (
        <label className="field-checkbox-label">
          <input
            type="checkbox"
            className="field-input field-input-checkbox"
            checked={!!value}
            onChange={(e) => onChange(e.target.checked)}
          />
          <span>{field.label}</span>
        </label>
      )
    
    default:
      return (
        <div className="field-error">
          Unsupported field type: {field.type}
        </div>
      )
  }
}
