import { useEffect, useRef } from 'react'
import { gsap, prefersReducedMotion } from '../lib/gsap'
import './Lens.css'

// a calm EAR trace across the lens — mostly flat, with one honest blink dip
const EAR_TRACE =
  '0,212 22,209 44,213 66,208 88,211 106,205 124,213 140,210 150,210 ' +
  '155,246 161,210 178,211 200,206 222,212 244,208 266,211 286,209 300,211'

export default function Lens() {
  const root = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (prefersReducedMotion() || !root.current) return
    const ctx = gsap.context(() => {
      gsap.to('.lens__glow', {
        opacity: 0.85,
        scale: 1.08,
        duration: 3.4,
        ease: 'sine.inOut',
        yoyo: true,
        repeat: -1,
      })
      gsap.to('.lens__scan', {
        yPercent: 620,
        duration: 6,
        ease: 'none',
        repeat: -1,
      })
      gsap.to('.lens__frame', {
        y: -8,
        duration: 5.5,
        ease: 'sine.inOut',
        yoyo: true,
        repeat: -1,
      })
      gsap.to('.lens__pupil', {
        opacity: 0.55,
        duration: 1.6,
        ease: 'sine.inOut',
        yoyo: true,
        repeat: -1,
      })
      // rare, deliberate blink — the driver blinks, the system stays quiet
      gsap
        .timeline({ repeat: -1, repeatDelay: 5 })
        .to('.lens__lid', { scaleY: 1, duration: 0.09, ease: 'power2.in' })
        .to('.lens__lid', { scaleY: 0, duration: 0.16, ease: 'power2.out' }, '+=0.04')
    }, root)
    return () => ctx.revert()
  }, [])

  return (
    <div className="lens" ref={root} aria-hidden="true">
      <div className="lens__chip lens__chip--ear u-label">EAR 0.31</div>
      <div className="lens__chip lens__chip--perclos u-label">PERCLOS 4%</div>

      <div className="lens__frame">
        <div className="lens__glow" />
        <svg className="lens__telemetry" viewBox="0 0 300 400" preserveAspectRatio="xMidYMid slice">
          <defs>
            <radialGradient id="lensCore" cx="50%" cy="42%" r="60%">
              <stop offset="0%" stopColor="#fff8ed" stopOpacity="0.22" />
              <stop offset="55%" stopColor="#fff8ed" stopOpacity="0.04" />
              <stop offset="100%" stopColor="#171110" stopOpacity="0" />
            </radialGradient>
          </defs>
          <rect x="0" y="0" width="300" height="400" fill="url(#lensCore)" />
          {/* guide rings */}
          <ellipse cx="150" cy="200" rx="120" ry="150" fill="none" stroke="#fff8ed" strokeOpacity="0.08" />
          <ellipse cx="150" cy="200" rx="78" ry="98" fill="none" stroke="#fff8ed" strokeOpacity="0.08" />
          {/* baseline */}
          <line x1="0" y1="212" x2="300" y2="212" stroke="#fff8ed" strokeOpacity="0.14" strokeDasharray="2 6" />
          {/* EAR trace */}
          <polyline points={EAR_TRACE} fill="none" stroke="#7fb0a3" strokeOpacity="0.85" strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round" />
          {/* reticle / pupil */}
          <g className="lens__pupil">
            <line x1="150" y1="176" x2="150" y2="224" stroke="#fff8ed" strokeOpacity="0.5" />
            <line x1="126" y1="200" x2="174" y2="200" stroke="#fff8ed" strokeOpacity="0.5" />
            <circle cx="150" cy="200" r="14" fill="none" stroke="#fff8ed" strokeOpacity="0.55" />
            <circle cx="150" cy="200" r="4" fill="#fff8ed" fillOpacity="0.85" />
          </g>
        </svg>
        <div className="lens__scan" />
        <div className="lens__lid" />
        <div className="lens__rim" />
      </div>

      <div className="lens__status">
        <span className="lens__dot" />
        <span className="u-label">Awake · baseline locked</span>
      </div>
    </div>
  )
}
