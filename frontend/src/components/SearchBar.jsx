const DEMO_ADDRESSES = [
  "42 Whale Beach Road, Whale Beach NSW 2107",
  "15 Ocean View Drive, Byron Bay NSW 2481",
  "8 Kangaroo Point Road, Kangaroo Point QLD 4169",
  "22 Firetrack Road, Upwey VIC 3158",
]

export default function SearchBar({ address, setAddress, onSearch, loading }) {
  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '12px', marginBottom: '10px' }}>
        <div style={{ flex: 1 }}>
          <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#374151', marginBottom: '6px', letterSpacing: '0.5px', textTransform: 'uppercase' }}>
            Property Address
          </label>
          <input
            type="text"
            value={address}
            onChange={e => setAddress(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && onSearch()}
            placeholder="e.g. 42 Whale Beach Road, Whale Beach NSW 2107"
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

      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        {DEMO_ADDRESSES.map(addr => (
          <button
            key={addr}
            onClick={() => { setAddress(addr); onSearch(addr) }}
            style={{
              fontSize: '12px',
              padding: '5px 12px',
              borderRadius: '6px',
              border: '1px solid #d1d5db',
              background: '#fff',
              color: '#6b7280',
              cursor: 'pointer',
              fontFamily: 'inherit',
            }}
          >
            ▶ {addr.split(',')[0]}
          </button>
        ))}
      </div>
    </div>
  )
}
