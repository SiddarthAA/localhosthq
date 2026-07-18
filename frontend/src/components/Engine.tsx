import Reveal from './Reveal'
import SectionHead from './SectionHead'
import './Engine.css'

const LAYERS = [
  { n: '01', name: 'Multi-signal extraction', desc: 'EAR, PERCLOS, blink rate & duration, head-nod, yawn — never one cue.' },
  { n: '02', name: 'Personal baseline', desc: 'The first ~12 seconds learn this driver’s normal; everything after is deviation, not a global constant.' },
  { n: '03', name: 'Corroboration & persistence', desc: 'The score rises only when independent signals agree and hold. One signal is a whisper; agreement is an alarm.', moat: true },
  { n: '04', name: 'Context gating', desc: 'Stay silent unless the vehicle is actually moving. No nagging a parked driver in a depot.' },
  { n: '05', name: 'Graduated escalation', desc: 'Calm note → soft chime → rising alarm, with hysteresis that backs off the moment the driver recovers.' },
  { n: '06', name: 'Adaptive duty-cycling', desc: 'Drop inference frame-rate when the driver is clearly alert; ramp back up the instant signals stir.' },
  { n: '07', name: 'Signed emission', desc: 'Tamper-evident Ed25519 events leave the edge. The video never does.' },
]

export default function Engine() {
  return (
    <section
      id="engine"
      className="engine section on-light"
      data-nav-theme="light"
    >
      <div className="shell">
        <SectionHead
          eyebrow="The engine"
          title="The co-pilot that knows when to speak"
          intro="Seven layers turn a raw camera feed into a decision. Detection is the easy part — everything above it is why RidewMe stays quiet when it should, and gets loud only when it has to."
        />

        <Reveal className="engine__moat">
          <span className="engine__moat-num">&ge;2</span>
          <p className="engine__moat-copy">
            independent signals must <em>agree</em> — and <em>persist</em> —
            before RidewMe says a word. Deciding when <strong>not</strong> to
            fire is the whole product.
          </p>
        </Reveal>

        <Reveal className="engine__layers" as="ol" stagger={0.06}>
          {LAYERS.map((l) => (
            <li className={`layer${l.moat ? ' layer--moat' : ''}`} key={l.n}>
              <span className="layer__n">{l.n}</span>
              <div className="layer__text">
                <h3 className="layer__name">{l.name}</h3>
                <p className="layer__desc">{l.desc}</p>
              </div>
              <span className="layer__arrow" aria-hidden="true">
                <svg viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>
              </span>
            </li>
          ))}
        </Reveal>
      </div>
    </section>
  )
}
