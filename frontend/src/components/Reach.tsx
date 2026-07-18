import Reveal from './Reveal'
import SectionHead from './SectionHead'
import './Reach.css'

const STATS = [
  { v: '0 bytes', k: 'video off-device' },
  { v: '$35-class', k: 'hardware, per cab' },
  { v: 'Milliseconds', k: 'to a decision' },
]

const FLEETS = [
  'Long-haul trucking', 'Taxi aggregators', 'Ride-hail', 'Intercity coaches',
  'Logistics & delivery', 'Last-mile', 'School transport', 'Corporate shuttles',
  'Mining haul', 'Construction fleets', 'Owner-operators', 'Cold-chain',
  'Passenger buses', 'Ambulance & EMS', 'Airport ground fleets', 'Utility fleets',
]

function Row({ items, reverse }: { items: string[]; reverse?: boolean }) {
  const track = [...items, ...items]
  return (
    <div className="marquee" aria-hidden="true">
      <div className={`marquee__track${reverse ? ' marquee__track--rev' : ''}`}>
        {track.map((f, i) => (
          <span className="chip" key={i}>
            {f}
          </span>
        ))}
      </div>
    </div>
  )
}

export default function Reach() {
  const half = Math.ceil(FLEETS.length / 2)
  return (
    <section id="reach" className="reach section on-dark" data-nav-theme="dark">
      <div className="shell">
        <Reveal className="reach__banner">
          {STATS.map((s, i) => (
            <div className="reach__stat" key={s.k}>
              <span className="reach__stat-v">{s.v}</span>
              <span className="reach__stat-k u-label">{s.k}</span>
              {i < STATS.length - 1 && <span className="reach__div" aria-hidden="true" />}
            </div>
          ))}
        </Reveal>

        <SectionHead
          eyebrow="Deploy anywhere"
          title="Built for every fleet on the road"
          className="reach__head"
        />
      </div>

      <div className="reach__marquees">
        <Row items={FLEETS.slice(0, half)} />
        <Row items={FLEETS.slice(half)} reverse />
        <ul className="sr-only">
          {FLEETS.map((f) => (
            <li key={f}>{f}</li>
          ))}
        </ul>
      </div>
    </section>
  )
}
