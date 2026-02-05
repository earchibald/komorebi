import { useState } from 'react'
import { Inbox } from './components/Inbox'
import { ChunkList } from './components/ChunkList'
import { Stats } from './components/Stats'
import { ProjectList } from './components/ProjectList'

type Tab = 'inbox' | 'all' | 'projects'

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('inbox')

  return (
    <div className="app">
      <header className="header">
        <h1>🌸 Komorebi</h1>
        <p className="subtitle">Cognitive Infrastructure Dashboard</p>
      </header>

      <Stats />

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
          className={`tab ${activeTab === 'projects' ? 'active' : ''}`}
          onClick={() => setActiveTab('projects')}
        >
          📁 Projects
        </button>
      </nav>

      <main className="content">
        {activeTab === 'inbox' && <Inbox />}
        {activeTab === 'all' && <ChunkList />}
        {activeTab === 'projects' && <ProjectList />}
      </main>

      <footer className="footer">
        <p>Komorebi v0.1.0 - Capture Now, Refine Later</p>
      </footer>
    </div>
  )
}

export default App
