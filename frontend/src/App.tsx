import { useState } from 'react'
import { Inbox } from './components/Inbox'
import { ChunkList } from './components/ChunkList'
import { StatsDashboard } from './components/StatsDashboard'
import { TimelineView } from './components/TimelineView'
import { ProjectList } from './components/ProjectList'
import { MCPPanel } from './components/MCPPanel'
import { ChunkDrawer } from './components/ChunkDrawer'
import { StagingArea } from './components/StagingArea'
import { BillingDashboard } from './components/BillingDashboard'
import { WatcherStatus } from './components/WatcherStatus'

type Tab = 'inbox' | 'all' | 'dashboard' | 'timeline' | 'projects' | 'mcp' | 'dispatch' | 'billing' | 'watcher'

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('inbox')

  return (
    <div className="app">
      <header className="header">
        <h1>🌸 Komorebi</h1>
        <p className="subtitle">Cognitive Infrastructure Dashboard</p>
      </header>

      <nav className="tabs">
        <button
          className={`tab ${activeTab === 'inbox' ? 'active' : ''}`}
          onClick={() => setActiveTab('inbox')}
        >
          📥 Inbox
        </button>
        <button
          className={`tab ${activeTab === 'all' ? 'active' : ''}`}
          onClick={() => setActiveTab('all')}
        >
          📋 All Chunks
        </button>
        <button
          className={`tab ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          📊 Dashboard
        </button>
        <button
          className={`tab ${activeTab === 'timeline' ? 'active' : ''}`}
          onClick={() => setActiveTab('timeline')}
        >
          📅 Timeline
        </button>
        <button
          className={`tab ${activeTab === 'projects' ? 'active' : ''}`}
          onClick={() => setActiveTab('projects')}
        >
          📁 Projects
        </button>
        <button
          className={`tab ${activeTab === 'mcp' ? 'active' : ''}`}
          onClick={() => setActiveTab('mcp')}
        >
          🔌 MCP
        </button>
        <button
          className={`tab ${activeTab === 'dispatch' ? 'active' : ''}`}
          onClick={() => setActiveTab('dispatch')}
        >
          📤 Dispatch
        </button>
        <button
          className={`tab ${activeTab === 'billing' ? 'active' : ''}`}
          onClick={() => setActiveTab('billing')}
        >
          💰 Billing
        </button>
        <button
          className={`tab ${activeTab === 'watcher' ? 'active' : ''}`}
          onClick={() => setActiveTab('watcher')}
        >
          👁️ Watcher
        </button>
      </nav>

      <main className="content">
        {activeTab === 'inbox' && <Inbox />}
        {activeTab === 'all' && <ChunkList />}
        {activeTab === 'dashboard' && <StatsDashboard />}
        {activeTab === 'timeline' && <TimelineView />}
        {activeTab === 'projects' && <ProjectList />}
        {activeTab === 'mcp' && <MCPPanel />}
        {activeTab === 'dispatch' && <StagingArea />}
        {activeTab === 'billing' && <BillingDashboard />}
        {activeTab === 'watcher' && <WatcherStatus />}
      </main>

      <footer className="footer">
        <p>Komorebi v0.7.0 - Capture Now, Refine Later</p>
      </footer>

      <ChunkDrawer />
    </div>
  )
}

export default App
