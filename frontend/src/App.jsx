import { useState, useRef } from 'react'
import Header from './components/Header'
import SearchBar from './components/SearchBar'
import Pipeline from './components/Pipeline'
import ScoresPanel from './components/ScoresPanel'

const TABS = ['Agent Activity', 'Risk Report', 'Risk Map']

const LAYER_DEFS = [
  { key: 'flood',    label: 'Flood Zone',             color: '#1a6fba' },
  { key: 'bushfire', label: 'Bushfire Prone Land',     color: '#cc4400' },
  { key: 'erosion',  label: 'Coastal Erosion Buffer',  color: '#8B6914' },
  { key: 'storm',    label: 'Storm Risk Radius',       color: '#5c35cc' },
]

const DEFAULT_VIS = { flood: true, bushfire: true, erosion: true, storm: false }

export default function App() {
  const [address, setAddress] = useState('')
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState(0)
  const [logLines, setLogLines] = useState([])
  const [scores, setScores] = useState(null)
  const [report, setReport] = useState('')
  const [mapHtml, setMapHtml] = useState('')
  const [mapLayers, setMapLayers] = useState({})
  const [layerVis, setLayerVis] = useState(DEFAULT_VIS)
  const [done, setDone] = useState(false)
  const abortRef = useRef(null)
  const mapContainerRef = useRef(null)

  const toggleLayer = (key, visible) => {
    setLayerVis(prev => ({ ...prev, [key]: visible }))
    const iframe = mapContainerRef.current?.querySelector('iframe')
    if (iframe?.contentWindow) {
      iframe.contentWindow.postMessage({ type: 'prism-toggle', layer: key, visible }, '*')
    }
  }

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
    setMapLayers({})
    setLayerVis(DEFAULT_VIS)
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
            else if (msg.type === 'map') {
              setMapHtml(msg.html)
              setMapLayers(msg.layers || {})
              setLayerVis(DEFAULT_VIS)
            }
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

  const noOverlays = mapHtml && !Object.values(mapLayers).some(Boolean)

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
            mapHtml ? (
              <div>
                {/* Layer toggles — outside the map iframe */}
                <div style={{
                  display: 'flex', gap: '24px', flexWrap: 'wrap',
                  padding: '10px 14px',
                  background: '#f8f9fa',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  marginBottom: '10px',
                }}>
                  {LAYER_DEFS.map(({ key, label, color }) => {
                    const hasData = Boolean(mapLayers[key])
                    return (
                      <label
                        key={key}
                        style={{
                          display: 'flex', alignItems: 'center', gap: '7px',
                          cursor: hasData ? 'pointer' : 'default',
                          opacity: hasData ? 1 : 0.38,
                          userSelect: 'none',
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={layerVis[key]}
                          disabled={!hasData}
                          onChange={e => toggleLayer(key, e.target.checked)}
                          style={{ accentColor: color, width: '14px', height: '14px', cursor: hasData ? 'pointer' : 'default' }}
                        />
                        <span style={{ fontSize: '12px', fontWeight: '600', color: hasData ? color : '#9ca3af' }}>
                          {label}
                        </span>
                        {!hasData && (
                          <span style={{ fontSize: '10px', color: '#bbb', fontStyle: 'italic' }}>no overlay</span>
                        )}
                      </label>
                    )
                  })}
                </div>

                {/* Map */}
                <div
                  ref={mapContainerRef}
                  dangerouslySetInnerHTML={{ __html: mapHtml }}
                  style={{ height: '460px', borderRadius: '8px', overflow: 'hidden', border: '1px solid #e5e7eb' }}
                />

                {/* No-overlay notice — outside the map */}
                {noOverlays && (
                  <div style={{
                    marginTop: '10px', padding: '9px 16px',
                    background: '#f0fdf4', border: '1px solid #bbf7d0',
                    borderRadius: '8px', fontSize: '13px', color: '#166534',
                    display: 'flex', alignItems: 'center', gap: '8px',
                  }}>
                    <span style={{ fontSize: '16px' }}>✓</span>
                    No active hazard overlays — all perils within normal thresholds for this location.
                  </div>
                )}
              </div>
            ) : (
              <p style={{ color: '#9ca3af', textAlign: 'center', paddingTop: '80px', fontSize: '14px' }}>Run an assessment to generate the interactive hazard map.</p>
            )
          )}
        </div>

        <p style={{ textAlign: 'center', fontSize: '11px', color: '#9ca3af', marginTop: '20px', lineHeight: '1.6' }}>
          <b>Live data:</b> Bureau of Meteorology · Geoscience Australia · DEA Satellite · Google Search (Gemini) · OpenStreetMap &nbsp;|&nbsp;
          PRISM prototype — not for production underwriting decisions.
        </p>
      </div>
    </div>
  )
}
