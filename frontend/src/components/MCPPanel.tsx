import { useState, useEffect } from 'react'
import { signal } from '@preact/signals-react'

// ─── Types ──────────────────────────────────────────────
export type MCPServerStatus = 'disconnected' | 'connecting' | 'connected' | 'error'

export interface MCPServer {
  id: string
  name: string
  server_type: string
  command: string
  args: string[]
  enabled: boolean
  status: MCPServerStatus
  last_error: string | null
}

export interface MCPTool {
  name: string
  description: string | null
  server_id: string
  input_schema: Record<string, unknown>
}

// ─── Signals ────────────────────────────────────────────
const mcpServers = signal<MCPServer[]>([])
const mcpTools = signal<MCPTool[]>([])
const mcpLoading = signal(false)
const mcpError = signal<string | null>(null)

const API_URL = '/api/v1'

// ─── Actions ────────────────────────────────────────────
async function fetchServers() {
  mcpLoading.value = true
  mcpError.value = null
  try {
    const res = await fetch(`${API_URL}/mcp/servers`)
    if (!res.ok) throw new Error('Failed to fetch servers')
    mcpServers.value = await res.json()
  } catch (e) {
    mcpError.value = e instanceof Error ? e.message : 'Unknown error'
  } finally {
    mcpLoading.value = false
  }
}

async function fetchTools() {
  try {
    const res = await fetch(`${API_URL}/mcp/tools`)
    if (!res.ok) throw new Error('Failed to fetch tools')
    mcpTools.value = await res.json()
  } catch (e) {
    console.error('Failed to fetch MCP tools:', e)
  }
}

async function connectServer(serverId: string) {
  try {
    const res = await fetch(`${API_URL}/mcp/servers/${serverId}/connect`, { method: 'POST' })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body.detail || 'Connect failed')
    }
    await fetchServers()
    await fetchTools()
  } catch (e) {
    mcpError.value = e instanceof Error ? e.message : 'Unknown error'
  }
}

async function disconnectServer(serverId: string) {
  try {
    await fetch(`${API_URL}/mcp/servers/${serverId}/disconnect`, { method: 'POST' })
    await fetchServers()
    await fetchTools()
  } catch (e) {
    mcpError.value = e instanceof Error ? e.message : 'Unknown error'
  }
}

async function reconnectServer(serverName: string) {
  try {
    const res = await fetch(`${API_URL}/mcp/${serverName}/reconnect`, { method: 'POST' })
    if (!res.ok) throw new Error('Reconnect failed')
    await fetchServers()
    await fetchTools()
  } catch (e) {
    mcpError.value = e instanceof Error ? e.message : 'Unknown error'
  }
}

async function callTool(toolName: string, args: Record<string, unknown>, capture = false, projectId?: string) {
  const params = new URLSearchParams()
  if (capture) params.set('capture', 'true')
  if (projectId) params.set('project_id', projectId)

  const res = await fetch(`${API_URL}/mcp/tools/${toolName}/call?${params}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(args),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || 'Tool call failed')
  }
  return res.json()
}

// ─── Status badge ───────────────────────────────────────
function StatusBadge({ status }: { status: MCPServerStatus }) {
  const map: Record<MCPServerStatus, { icon: string; label: string; className: string }> = {
    connected:    { icon: '🟢', label: 'Connected',    className: 'badge-connected' },
    connecting:   { icon: '🟡', label: 'Connecting…',  className: 'badge-connecting' },
    disconnected: { icon: '🔴', label: 'Disconnected', className: 'badge-disconnected' },
    error:        { icon: '🔴', label: 'Error',        className: 'badge-error' },
  }
  const info = map[status] ?? map.disconnected
  return <span className={`mcp-badge ${info.className}`}>{info.icon} {info.label}</span>
}

// ─── Tool call modal ────────────────────────────────────
function ToolCallModal({
  tool,
  onClose,
}: {
  tool: MCPTool
  onClose: () => void
}) {
  const [argsText, setArgsText] = useState('{}')
  const [capture, setCapture] = useState(true)
  const [result, setResult] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const run = async () => {
    setRunning(true)
    setErr(null)
    setResult(null)
    try {
      const args = JSON.parse(argsText)
      const res = await callTool(tool.name, args, capture)
      setResult(JSON.stringify(res, null, 2))
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <h3>🛠️ {tool.name}</h3>
        {tool.description && <p className="text-secondary">{tool.description}</p>}

        <label>Arguments (JSON)</label>
        <textarea
          value={argsText}
          onChange={e => setArgsText(e.target.value)}
          rows={6}
          className="mcp-textarea"
        />

        <label className="mcp-checkbox">
          <input
            type="checkbox"
            checked={capture}
            onChange={e => setCapture(e.target.checked)}
          />
          Capture result as Chunk
        </label>

        <div className="modal-actions">
          <button onClick={run} disabled={running} className="btn-primary">
            {running ? '⏳ Running…' : '▶ Execute'}
          </button>
          <button onClick={onClose} className="btn-secondary">Close</button>
        </div>

        {err && <pre className="mcp-error">{err}</pre>}
        {result && (
          <pre className="mcp-result">
            {result}
          </pre>
        )}
      </div>
    </div>
  )
}

// ─── Main Panel ─────────────────────────────────────────
export function MCPPanel() {
  const [expandedServer, setExpandedServer] = useState<string | null>(null)
  const [selectedTool, setSelectedTool] = useState<MCPTool | null>(null)
  const [toolSearch, setToolSearch] = useState('')

  useEffect(() => {
    fetchServers()
    fetchTools()
  }, [])

  const servers = mcpServers.value
  const tools = mcpTools.value
  const loading = mcpLoading.value
  const error = mcpError.value

  const filteredTools = toolSearch
    ? tools.filter(t =>
        t.name.toLowerCase().includes(toolSearch.toLowerCase()) ||
        (t.description ?? '').toLowerCase().includes(toolSearch.toLowerCase())
      )
    : tools

  const toolsByServer = (serverId: string) =>
    filteredTools.filter(t => t.server_id === serverId)

  return (
    <div className="mcp-panel">
      <div className="mcp-header">
        <h2>🔌 MCP Servers</h2>
        <button onClick={() => { fetchServers(); fetchTools() }} className="btn-secondary" disabled={loading}>
          {loading ? '⏳' : '🔄'} Refresh
        </button>
      </div>

      {error && <div className="mcp-error">{error}</div>}

      {servers.length === 0 && !loading && (
        <p className="text-secondary">No MCP servers registered. Add servers via config/mcp_servers.json or the API.</p>
      )}

      <div className="mcp-server-list" data-testid="mcp-server-list">
        {servers.map(server => (
          <div key={server.id} className="mcp-server-card">
            <div className="mcp-server-row">
              <div className="mcp-server-info">
                <strong>{server.name}</strong>
                <StatusBadge status={server.status} />
                <span className="text-secondary mcp-command">{server.command} {server.args.join(' ')}</span>
              </div>
              <div className="mcp-server-actions">
                {server.status === 'connected' ? (
                  <button onClick={() => disconnectServer(server.id)} className="btn-secondary btn-sm">
                    ⏹ Disconnect
                  </button>
                ) : (
                  <button onClick={() => connectServer(server.id)} className="btn-primary btn-sm">
                    ▶ Connect
                  </button>
                )}
                <button
                  onClick={() => reconnectServer(server.name)}
                  className="btn-secondary btn-sm"
                  title="Reconnect"
                >
                  🔁
                </button>
                <button
                  onClick={() => setExpandedServer(expandedServer === server.id ? null : server.id)}
                  className="btn-secondary btn-sm"
                >
                  {expandedServer === server.id ? '▲' : '▼'} Tools
                </button>
              </div>
            </div>

            {server.last_error && (
              <div className="mcp-server-error">⚠️ {server.last_error}</div>
            )}

            {expandedServer === server.id && (
              <div className="mcp-tool-list" data-testid="tool-browser">
                {toolsByServer(server.id).length === 0 ? (
                  <p className="text-secondary">No tools available (server may be disconnected)</p>
                ) : (
                  toolsByServer(server.id).map(tool => (
                    <div key={tool.name} className="mcp-tool-item">
                      <div>
                        <strong>{tool.name}</strong>
                        {tool.description && <span className="text-secondary"> — {tool.description}</span>}
                      </div>
                      <button
                        onClick={() => setSelectedTool(tool)}
                        className="btn-primary btn-sm"
                      >
                        Call
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Global tool search */}
      {tools.length > 0 && (
        <div className="mcp-tool-search">
          <h3>🔍 All Tools ({filteredTools.length})</h3>
          <input
            type="text"
            placeholder="Search tools…"
            value={toolSearch}
            onChange={e => setToolSearch(e.target.value)}
            className="mcp-search-input"
          />
          <div className="mcp-all-tools">
            {filteredTools.map(tool => (
              <div key={tool.name} className="mcp-tool-item">
                <div>
                  <strong>{tool.name}</strong>
                  {tool.description && <span className="text-secondary"> — {tool.description}</span>}
                </div>
                <button onClick={() => setSelectedTool(tool)} className="btn-primary btn-sm">
                  Call
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {selectedTool && (
        <ToolCallModal tool={selectedTool} onClose={() => setSelectedTool(null)} />
      )}
    </div>
  )
}
