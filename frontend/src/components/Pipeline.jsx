const AGENTS = [
  { name: 'Data Harvesting',  key: 'Data Harvesting Agent activated' },
  { name: 'Risk Analysis',    key: 'Risk Analysis Agent activated' },
  { name: 'Validation',       key: 'Validation' },
  { name: 'Report',           key: 'Communication Agent activated' },
]

const EMOJI_RE = /^[\u{1F000}-\u{1FFFF}\u{2600}-\u{27FF}\u{2300}-\u{23FF}✅❌⚠️🏁📍🔍📊🔎📝✔]\s*/u

function detectStage(lines) {
  let stage = 0
  for (const line of lines) {
    if (line.includes('Data Harvesting Agent activated')) stage = 1
    else if (line.includes('Risk Analysis Agent activated')) stage = 2
    else if (line.includes('Validation') && line.includes('Agent activated')) stage = 3
    else if (line.includes('Communication Agent activated')) stage = 4
  }
  return stage
}

function ChevronStep({ name, state, isFirst, isLast }) {
  const styles = {
    complete: { bg: '#304E4D', color: '#fff',    label: 'COMPLETE' },
    running:  { bg: '#D2B589', color: '#304E4D', label: 'RUNNING…' },
    waiting:  { bg: '#f3f4f6', color: '#9ca3af', label: 'WAITING'  },
  }[state]

  const clip = isFirst
    ? 'polygon(0 0, calc(100% - 16px) 0, 100% 50%, calc(100% - 16px) 100%, 0 100%)'
    : isLast
    ? 'polygon(0 0, 100% 0, 100% 100%, 0 100%, 16px 50%)'
    : 'polygon(0 0, calc(100% - 16px) 0, 100% 50%, calc(100% - 16px) 100%, 0 100%, 16px 50%)'

  return (
    <div style={{ flex: 1 }}>
      <div style={{
        background: styles.bg,
        clipPath: clip,
        padding: '14px 24px 14px 28px',
        textAlign: 'center',
        transition: 'background 0.4s ease',
      }}>
        <div style={{ fontSize: '11px', fontWeight: '700', letterSpacing: '0.8px', textTransform: 'uppercase', color: styles.color, fontFamily: "'Segoe UI', sans-serif" }}>
          {name}
        </div>
        <div style={{
          fontSize: '10px', fontWeight: '600', letterSpacing: '0.5px', color: styles.color,
          opacity: 0.75, marginTop: '3px',
          animation: state === 'running' ? 'pulse 1.5s infinite' : 'none',
          fontFamily: "'Segoe UI', sans-serif",
        }}>
          {styles.label}
        </div>
      </div>
    </div>
  )
}

function LogLine({ line }) {
  if (line.startsWith('─')) return <div style={{ borderTop: '1px solid #e5e7eb', margin: '6px 0' }} />

  const isHeader = /^[📍🔍📊🔎📝]/.test(line)
  const isSuccess = line.startsWith('✅')
  const isError   = line.startsWith('❌') || line.startsWith('⚠️')
  const isFinish  = line.startsWith('🏁')
  const isSub     = line.trim().startsWith('↳')

  let color = '#374151', weight = '400'
  if (isHeader)  { color = '#D2B589'; weight = '600' }
  if (isSuccess) { color = '#2e7d32'; weight = '600' }
  if (isError)   { color = '#c62828'; weight = '600' }
  if (isFinish)  { color = '#1565c0'; weight = '700' }
  if (isSub)     { color = '#6b7280' }

  // Strip leading emoji
  const clean = line.replace(EMOJI_RE, '').trim()

  const html = clean
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')

  return (
    <div
      style={{
        padding: '2px 0',
        color,
        fontWeight: weight,
        fontSize: '13px',
        fontFamily: "'Segoe UI', sans-serif",
      }}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}

export default function Pipeline({ lines, done }) {
  const stage = detectStage(lines)

  return (
    <div>
      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }`}</style>

      <div style={{ display: 'flex', gap: '3px', marginBottom: '16px' }}>
        {AGENTS.map((agent, i) => {
          const idx = i + 1
          const state = (done && idx <= 4) || idx < stage ? 'complete'
            : idx === stage && !done ? 'running' : 'waiting'
          return (
            <ChevronStep key={agent.name} name={agent.name} state={state}
              isFirst={i === 0} isLast={i === AGENTS.length - 1} />
          )
        })}
      </div>

      <div style={{
        background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: '8px',
        padding: '16px', minHeight: '240px', maxHeight: '400px', overflowY: 'auto',
      }}>
        {lines.length === 0
          ? <span style={{ color: '#9ca3af', fontSize: '13px', fontFamily: "'Segoe UI', sans-serif" }}>Waiting for assessment to start…</span>
          : lines.map((line, i) => <LogLine key={i} line={line} />)
        }
      </div>
    </div>
  )
}
