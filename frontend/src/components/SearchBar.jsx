export default function SearchBar({ address, setAddress, onSearch, loading }) {
  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '12px' }}>
        <div style={{ flex: 1 }}>
          <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#374151', marginBottom: '6px', letterSpacing: '0.5px', textTransform: 'uppercase' }}>
            Property Address
          </label>
          <input
            type="text"
            value={address}
            onChange={e => setAddress(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && onSearch()}
            placeholder="Enter any Australian property address…"
            style={{
              width: '100%',
              padding: '10px 16px',
              border: '1.5px solid #d1d5db',
              borderRadius: '8px',
              fontSize: '14px',
              outline: 'none',
              fontFamily: 'inherit',
              color: '#111827',
              background: '#fff',
              boxSizing: 'border-box',
            }}
          />
        </div>
        <button
          onClick={onSearch}
          disabled={loading}
          style={{
            background: loading ? '#e5c99a' : '#D2B589',
            color: '#304E4D',
            border: 'none',
            borderRadius: '999px',
            textTransform: 'uppercase',
            fontWeight: '700',
            letterSpacing: '1.5px',
            fontSize: '13px',
            padding: '10px 32px',
            minWidth: '140px',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontFamily: 'inherit',
            whiteSpace: 'nowrap',
          }}
        >
          {loading ? 'Running…' : 'SEARCH'}
        </button>
      </div>
    </div>
  )
}
