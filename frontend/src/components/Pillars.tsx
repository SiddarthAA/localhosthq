import Reveal from './Reveal'
import SectionHead from './SectionHead'
import './Pillars.css'

const ICONS: Record<string, React.ReactNode> = {
  eye: (
    <>
      <path d="M2 12s3.5-6.5 10-6.5S22 12 22 12s-3.5 6.5-10 6.5S2 12 2 12Z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  edge: (
    <>
      <rect x="6" y="6" width="12" height="12" rx="1.5" />
      <path d="M9.5 3v3M14.5 3v3M9.5 18v3M14.5 18v3M3 9.5h3M3 14.5h3M18 9.5h3M18 14.5h3" />
    </>
  ),
  privacy: (
    <>
      <path d="M3 3l18 18" />
      <path d="M10.5 5.2A9.7 9.7 0 0 1 12 5.1c6.5 0 10 6.9 10 6.9a17 17 0 0 1-2.4 3.3M6.2 6.3C3.5 8.1 2 12 2 12s3.5 6.9 10 6.9a9.5 9.5 0 0 0 3.6-.7" />
    </>
  ),
  evidence: (
    <>
      <path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6l7-3Z" />
      <path d="M9 12l2 2 4-4" />
    </>
  ),
}

const PILLARS = [
  {
    icon: 'eye',
    title: 'It earns every alert',
    body: 'Most monitors fire on every blink and glance until drivers stop believing them and cover the lens. RideWMe learns each driver’s normal in seconds, then waits for multiple signs of fatigue to agree before it says a word. The result is the one thing safety tech actually needs: alerts drivers trust, and act on.',
  },
  {
    icon: 'edge',
    title: 'It lives on the edge',
    body: 'No cloud round-trip. No dead-zone blind spots. The entire decision engine runs on a single low-cost board inside the vehicle, making the call in milliseconds — whether you’re in a depot or a canyon with no signal.',
  },
  {
    icon: 'privacy',
    title: 'Your video never leaves the vehicle',
    body: 'The camera feed is read on the device and discarded frame by frame. Only signed decisions ever travel out — never an image. Privacy for the driver, and a system that’s clean by design, not by promise.',
  },
  {
    icon: 'evidence',
    title: 'Evidence that holds up',
    body: 'Every event is written to a tamper-evident, cryptographically signed record. When an incident is disputed, you hold proof that stands — for the insurer, and in court.',
  },
]

export default function Pillars() {
  return (
    <section
      id="why"
      className="pillars section on-light"
      data-nav-theme="light"
    >
      <div className="shell">
        <SectionHead
          eyebrow="On-device safety intelligence"
          title="Built to be believed"
        />
        <Reveal className="pillars__grid" stagger={0.1}>
          {PILLARS.map((p) => (
            <article className="pillar" key={p.title}>
              <span className="pillar__icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                  {ICONS[p.icon]}
                </svg>
              </span>
              <h3 className="pillar__title">{p.title}</h3>
              <span className="rule" />
              <p className="pillar__body">{p.body}</p>
            </article>
          ))}
        </Reveal>
      </div>
    </section>
  )
}
