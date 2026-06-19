const HoneycombSVG = () => (
  <svg
    viewBox="0 0 480 210"
    preserveAspectRatio="xMaxYMax meet"
    xmlns="http://www.w3.org/2000/svg"
    style={{
      position: 'absolute', right: 0, bottom: 0,
      width: '380px', height: '120px', pointerEvents: 'none',
      transform: 'perspective(380px) rotateX(45deg)',
      transformOrigin: 'bottom right',
    }}
  >
    <defs>
      <radialGradient id="hc-grad" cx="1" cy="1" r="1.3" gradientUnits="objectBoundingBox">
        <stop offset="0%" stopColor="white" />
        <stop offset="55%" stopColor="white" stopOpacity="0.5" />
        <stop offset="100%" stopColor="black" />
      </radialGradient>
      <mask id="hc-mask">
        <rect width="480" height="210" fill="url(#hc-grad)" />
      </mask>
    </defs>
    <g mask="url(#hc-mask)" fill="none" stroke="rgba(190,230,210,0.55)" strokeWidth="1.5">
      {[
        [0,26],[45,26],[90,26],[135,26],[180,26],[225,26],[270,26],[315,26],[360,26],[405,26],[450,26],
        [23,65],[68,65],[113,65],[158,65],[203,65],[248,65],[293,65],[338,65],[383,65],[428,65],[473,65],
        [0,104],[45,104],[90,104],[135,104],[180,104],[225,104],[270,104],[315,104],[360,104],[405,104],[450,104],
        [23,143],[68,143],[113,143],[158,143],[203,143],[248,143],[293,143],[338,143],[383,143],[428,143],[473,143],
        [0,182],[45,182],[90,182],[135,182],[180,182],[225,182],[270,182],[315,182],[360,182],[405,182],[450,182],
      ].map(([cx, cy], i) => {
        const r=26, hw=23, hh=13
        return (
          <polygon key={i} points={`${cx},${cy-r} ${cx+hw},${cy-hh} ${cx+hw},${cy+hh} ${cx},${cy+r} ${cx-hw},${cy+hh} ${cx-hw},${cy-hh}`} />
        )
      })}
    </g>
  </svg>
)

export default function Header() {
  return (
    <div style={{
      background: '#304E4D',
      padding: '28px 48px',
      borderRadius: '12px',
      marginBottom: '16px',
      position: 'relative',
      overflow: 'hidden',
      display: 'flex',
      alignItems: 'center',
    }}>
      <div style={{ position: 'relative', zIndex: 2 }}>
        <h1 style={{
          color: '#fff',
          fontSize: '64px',
          fontWeight: '900',
          letterSpacing: '4px',
          lineHeight: 1,
          margin: 0,
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        }}>
          PRISM
        </h1>
        <p style={{ color: '#D2B589', marginTop: '8px', fontSize: '13px', letterSpacing: '0.3px' }}>
          Property Risk Intelligence &amp; Synthesis Manager &nbsp;·&nbsp;
          Natural Hazard Assessment for Luxury Coastal &amp; Bushland Properties
        </p>
      </div>
      <HoneycombSVG />
    </div>
  )
}
