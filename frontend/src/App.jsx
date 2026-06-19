import { useState, useRef } from 'react'
import Header from './components/Header'
import SearchBar from './components/SearchBar'
import Pipeline from './components/Pipeline'
import ScoresPanel from './components/ScoresPanel'

const TABS = ['Agent Activity', 'Risk Report', 'Risk Map']

export default function App() {
  const [address, setAddress] = useState('')
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState(0)
  const [logLines, setLogLines] = useState([])
  const [scores, setScores] = useState(null)
  const [report, setReport] = useState('')
  const [mapHtml, setMapHtml] = useState('')
  const [done, setDone] = useState(false)
  const abortRef = useRef(null)

  const runAssessment = async (addr) => {
    const target = typeof addr === 'string' ? addr : address
    if (!target.trim()) return

    if (abortRef.current) abortRef.current.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setLoading(true)
    setDone(false)
    setLogLines([])
    setScores(null)
    setReport('')
    setMapHtml('')
    setActiveTab(0)

    try {
      const res = await fetch('/api/assess', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: target }),
        signal: controller.signal,
      })

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done: streamDone, value } = await reader.read()
        if (streamDone) break
        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop()
        for (const part of parts) {
          const line = part.replace(/^data: /, '').trim()
          if (!line) continue
          try {
            const msg = JSON.parse(line)
            if (msg.type === 'log') setLogLines(prev => [...prev, msg.line])
            else if (msg.type === 'scores') setScores(msg.data)
            else if (msg.type === 'report') setReport(msg.markdown)
            else if (msg.type === 'map') setMapHtml(msg.html)
            else if (msg.type === 'done') setDone(true)
            else if (msg.type === 'error') setLogLines(prev => [...prev, `❌ ${msg.message}`])
          } catch {}
        }
      }
    } catch (e) {
      if (e.name !== 'AbortError') setLogLines(prev => [...prev, `❌ Connection error: ${e.message}`])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: '#f0f2f5', padding: '32px 24px' }}>
      <div style={{ maxWidth: '960px', margin: '0 auto' }}>

        <Header />

        <SearchBar address={address} setAddress={setAddress} onSearch={runAssessment} loading={loading} />

        {/* Tabs */}
        <div style={{ borderBottom: '2px solid #e5e7eb', marginBottom: '0' }}>
          <div style={{ display: 'flex', gap: '0' }}>
            {TABS.map((tab, i) => (
              <button
                key={tab}
                onClick={() => setActiveTab(i)}
                style={{
                  padding: '10px 24px',
                  fontSize: '13px',
                  fontWeight: '600',
                  border: 'none',
                  borderBottom: activeTab === i ? '2px solid #304E4D' : '2px solid transparent',
                  marginBottom: '-2px',
                  background: 'transparent',
                  color: activeTab === i ? '#304E4D' : '#6b7280',
                  cursor: 'pointer',
                  letterSpacing: '0.3px',
                  transition: 'color 0.15s',
                }}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* Tab content */}
        <div style={{
          background: '#fff',
          borderRadius: '0 0 12px 12px',
          padding: '24px',
          boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
          border: '1px solid #e5e7eb',
          borderTop: 'none',
          minHeight: '320px',
        }}>
          {activeTab === 0 && <Pipeline lines={logLines} done={done} />}
          {activeTab === 1 && (
            scores
              ? <ScoresPanel scores={scores} report={report} />
              : <p style={{ color: '#9ca3af', textAlign: 'center', paddingTop: '80px', fontSize: '14px' }}>Run an assessment to see risk scores.</p>
          )}
          {activeTab === 2 && (
            mapHtml
              ? <div dangerouslySetInnerHTML={{ __html: mapHtml }} style={{ height: '500px', borderRadius: '8px', overflow: 'hidden' }} />
              : <p style={{ color: '#9ca3af', textAlign: 'center', paddingTop: '80px', fontSize: '14px' }}>Run an assessment to generate the interactive hazard map.</p>
          )}
        </div>

        <p style={{ textAlign: 'center', fontSize: '11px', color: '#9ca3af', marginTop: '20px', lineHeight: '1.6' }}>
          <b>Live data:</b> Bureau of Meteorology · Geoscience Australia · OpenStreetMap &nbsp;|&nbsp;
          <b>Simulated:</b> CoreLogic · ISI Claims · Sentinel-2 · Council overlays &nbsp;|&nbsp;
          PRISM prototype — not for production underwriting decisions.
        </p>
      </div>
    </div>
  )
}
