const LINE =
  '0,95 70,92 110,178 200,180 235,178 275,62 315,60 350,150 400,120 440,118'
const AREA = `0,230 ${LINE} 440,230`

/** Adaptive duty-cycle: inference fps throttles down when the driver is
    clearly alert, then snaps back the instant signals stir. */
export default function DutyCycle() {
  return (
    <div className="duty" aria-hidden="true">
      <div className="duty__head">
        <span className="u-label">Adaptive duty-cycle</span>
        <span className="u-label duty__unit">inference fps</span>
      </div>
      <svg viewBox="0 0 440 240" className="duty__chart" preserveAspectRatio="none">
        <defs>
          <linearGradient id="dutyFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--ink)" stopOpacity="0.14" />
            <stop offset="100%" stopColor="var(--ink)" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[40, 120, 200].map((y) => (
          <line key={y} x1="0" y1={y} x2="440" y2={y} stroke="var(--ink)" strokeOpacity="0.08" />
        ))}
        <polygon points={AREA} fill="url(#dutyFill)" />
        <polyline
          points={LINE}
          fill="none"
          stroke="var(--ink)"
          strokeWidth="2.5"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {/* throttled plateau */}
        <circle cx="200" cy="180" r="4" fill="var(--signal)" />
        <text x="150" y="205" className="duty__anno">throttled · alert</text>
        {/* full-attention spike */}
        <circle cx="295" cy="61" r="4" fill="var(--alert)" />
        <text x="300" y="46" className="duty__anno duty__anno--alert">full fps · signals stir</text>
        <line className="duty__scan" x1="0" y1="0" x2="0" y2="240" stroke="var(--ink)" strokeOpacity="0.18" strokeWidth="1.5" />
      </svg>
    </div>
  )
}
