import { useEffect, useState, FormEvent } from 'react'
import { projects, loading, fetchProjects, createProject } from '../store'
import type { Project } from '../store'

export function ProjectList() {
  const [isCreating, setIsCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDescription, setNewDescription] = useState('')

  useEffect(() => {
    fetchProjects()
  }, [])

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault()
    if (!newName.trim()) return

    try {
      await createProject(newName.trim(), newDescription.trim() || undefined)
      setNewName('')
      setNewDescription('')
      setIsCreating(false)
    } catch {
      // Error handled in store
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2>Projects</h2>
        <button
          className="inbox-button"
          onClick={() => setIsCreating(!isCreating)}
          style={{ padding: '0.5rem 1rem' }}
        >
          {isCreating ? '✕ Cancel' : '+ New Project'}
        </button>
      </div>

      {isCreating && (
        <form onSubmit={handleCreate} style={{ marginBottom: '1.5rem', padding: '1rem', background: 'var(--bg-primary)', borderRadius: '8px' }}>
          <input
            className="inbox-input"
            type="text"
            placeholder="Project name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            style={{ marginBottom: '0.5rem', width: '100%' }}
          />
          <input
            className="inbox-input"
            type="text"
            placeholder="Description (optional)"
            value={newDescription}
            onChange={(e) => setNewDescription(e.target.value)}
            style={{ marginBottom: '0.5rem', width: '100%' }}
          />
          <button className="inbox-button" type="submit" disabled={!newName.trim()}>
            Create Project
          </button>
        </form>
      )}

      {loading.value && projects.value.length === 0 ? (
        <div className="loading">Loading projects...</div>
      ) : projects.value.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📁</div>
          <p>No projects yet. Create one to organize your chunks!</p>
        </div>
      ) : (
        <div className="project-list">
          {projects.value.map((project: Project) => (
            <div key={project.id} className="project-card">
              <div className="project-name">{project.name}</div>
              {project.description && (
                <div className="project-description">{project.description}</div>
              )}
              <div className="project-stats">
                <span>📝 {project.chunk_count} chunks</span>
                <span>📅 {new Date(project.created_at).toLocaleDateString()}</span>
              </div>
              {project.context_summary && (
                <div style={{ marginTop: '1rem', padding: '0.75rem', background: 'var(--bg-secondary)', borderRadius: '6px', fontSize: '0.9rem' }}>
                  <strong>Context:</strong>
                  <p style={{ marginTop: '0.5rem', color: 'var(--text-secondary)' }}>
                    {project.context_summary.slice(0, 200)}
                    {project.context_summary.length > 200 && '...'}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
