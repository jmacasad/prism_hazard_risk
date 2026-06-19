import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

function scoreColor(s) {
  if (s >= 75) return '#d32f2f'
  if (s >= 55) return '#f57c00'
  if (s >= 35) return '#f9a825'
  return '#388e3c'
}

function Badge({ score }) {
  return (
    <span style={{
      display: 'inline-block',
      background: scoreColor(score),
      color: '#fff',
      padding: '3px 14px',
      borderRadius: '4px',
      fontWeight: '700',
      fontSize: '13px',
      minWidth: '52px',
      textAlign: 'center',
    }}>
      {score}
    </span>
  )
}

export default function ScoresPanel({ scores, report }) {
  if (!scores) return null
  const { perils = {}, overall_score = 0, risk_band = '', premium_loading = '', confidence = '' } = scores

  return (
    <div style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif' }}>
      {/* Overall score */}
      <div style={{ textAlign: 'center', padding: '24px 0 20px' }}>
        <div style={{ fontSize: '72px', fontWeight: '900', lineHeight: 1, color: scoreColor(overall_score) }}>
          {overall_score}
        </div>
        <div style={{ fontSize: '18px', fontWeight: '800', marginTop: '6px', color: '#1f2937', letterSpacing: '0.5px' }}>
          {risk_band} RISK
        </div>
        <div style={{ color: '#6b7280', fontSize: '13px', marginTop: '6px' }}>
          Confidence: <b>{confidence}</b> &nbsp;·&nbsp; Recommended premium loading: <b>{premium_loading}</b>
        </div>
      </div>

      {/* Perils table */}
      <table style={{ width: '100%', borderCollapse: 'collapse', border: '1px solid #e5e7eb', borderRadius: '8px', overflow: 'hidden', fontSize: '13px' }}>
        <thead>
          <tr style={{ background: '#f9fafb' }}>
            <th style={{ padding: '10px 16px', textAlign: 'left', color: '#6b7280', fontWeight: '600', width: '130px' }}>Peril</th>
            <th style={{ padding: '10px 16px', textAlign: 'center', color: '#6b7280', fontWeight: '600', width: '110px' }}>Score /100</th>
            <th style={{ padding: '10px 16px', textAlign: 'left', color: '#6b7280', fontWeight: '600' }}>Key Risk Factors</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(perils).map(([name, data]) => (
            <tr key={name} style={{ borderTop: '1px solid #f0f0f0' }}>
              <td style={{ padding: '10px 16px', fontWeight: '600', textTransform: 'capitalize', color: '#111827' }}>{name}</td>
              <td style={{ padding: '10px 16px', textAlign: 'center' }}><Badge score={data.score || 0} /></td>
              <td style={{ padding: '10px 16px', color: '#4b5563', fontSize: '12px' }}>{(data.factors || []).join(' · ')}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Full report */}
      {report && (
        <div style={{ marginTop: '24px', borderTop: '1px solid #e5e7eb', paddingTop: '20px' }}>
          <h3 style={{ fontSize: '12px', fontWeight: '700', color: '#6b7280', marginBottom: '16px', letterSpacing: '1px', textTransform: 'uppercase' }}>
            Full Assessment Report
          </h3>
          <div style={{ fontSize: '13px', lineHeight: '1.8', color: '#374151' }}>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h1: ({children}) => null,
                h2: ({children}) => (
                  <h2 style={{ fontSize: '14px', fontWeight: '700', color: '#111827', margin: '20px 0 8px', letterSpacing: '0.3px', textTransform: 'uppercase', borderBottom: '1px solid #e5e7eb', paddingBottom: '6px' }}>
                    {children}
                  </h2>
                ),
                h3: ({children}) => (
                  <h3 style={{ fontSize: '13px', fontWeight: '700', color: '#304E4D', margin: '14px 0 6px' }}>{children}</h3>
                ),
                p: ({children}) => (
                  <p style={{ margin: '0 0 10px', color: '#374151' }}>{children}</p>
                ),
                strong: ({children}) => (
                  <strong style={{ fontWeight: '700', color: '#111827' }}>{children}</strong>
                ),
                hr: () => null,
                blockquote: ({children}) => (
                  <blockquote style={{ borderLeft: '3px solid #D2B589', paddingLeft: '12px', color: '#6b7280', margin: '8px 0', fontStyle: 'italic' }}>{children}</blockquote>
                ),
                table: ({children}) => (
                  <table style={{ width: '100%', borderCollapse: 'collapse', margin: '10px 0', fontSize: '12px' }}>{children}</table>
                ),
                th: ({children}) => (
                  <th style={{ padding: '8px 12px', background: '#f9fafb', border: '1px solid #e5e7eb', textAlign: 'left', fontWeight: '600', color: '#374151' }}>{children}</th>
                ),
                td: ({children}) => (
                  <td style={{ padding: '8px 12px', border: '1px solid #e5e7eb', color: '#374151' }}>{children}</td>
                ),
                li: ({children}) => (
                  <li style={{ margin: '3px 0', paddingLeft: '4px' }}>{children}</li>
                ),
                ul: ({children}) => (
                  <ul style={{ paddingLeft: '20px', margin: '6px 0' }}>{children}</ul>
                ),
                ol: ({children}) => (
                  <ol style={{ paddingLeft: '20px', margin: '6px 0' }}>{children}</ol>
                ),
              }}
            >
              {report}
            </ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  )
}
