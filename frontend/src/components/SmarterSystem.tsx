import { useState } from 'react'
import SectionHead from './SectionHead'
import DutyCycle from './DutyCycle'
import './SmarterSystem.css'

const ITEMS = [
  {
    title: 'No alarm fatigue',
    body: 'A system that cries wolf gets unplugged. RidewMe stays silent until fatigue is real, so drivers keep it on and keep trusting it — the only way driver-safety tech ever actually works.',
    caption: 'Alerts fire only when signals agree and persist — not on every blink.',
  },
  {
    title: 'Works where the signal doesn’t',
    body: 'Highways have dead zones, and cloud systems go dark inside them. RidewMe runs entirely on the device, so it protects the driver on the open road at exactly the moments that matter most.',
    caption: 'The whole decision loop runs on-device — no network, no blind spots.',
  },
  {
    title: 'Fits the fleet you already run',
    body: 'No new trucks. No rip-and-replace. A small device retrofits to the vehicles you already own — protecting drivers without touching your capital budget.',
    caption: 'One ~$35-class board per cab. Retrofit, not replace.',
  },
  {
    title: 'Frugal by design',
    body: 'When the driver is alert, the engine throttles itself down to sip power and stay cool; the instant anything changes, it snaps back to full attention. Built for a fanless board in a hot cab, not a server rack.',
    caption: 'Inference frame-rate drops when the driver is clearly alert, then snaps back the moment signals stir.',
  },
]

export default function SmarterSystem() {
  const [open, setOpen] = useState(0)

  return (
    <section id="how" className="smarter section on-light" data-nav-theme="light">
      <div className="shell">
        <SectionHead
          eyebrow="Why it wins in the real world"
          title="A smarter system, end to end"
        />

        <div className="smarter__grid">
          <ul className="acc">
            {ITEMS.map((it, i) => {
              const isOpen = open === i
              return (
                <li className={`acc__item${isOpen ? ' is-open' : ''}`} key={it.title}>
                  <button
                    className="acc__head"
                    onClick={() => setOpen(isOpen ? -1 : i)}
                    aria-expanded={isOpen}
                  >
                    <span className="acc__title">{it.title}</span>
                    <span className="acc__sign" aria-hidden="true" />
                  </button>
                  <div className="acc__panel">
                    <div className="acc__panel-in">
                      <p className="acc__body">{it.body}</p>
                    </div>
                  </div>
                </li>
              )
            })}
          </ul>

          <div className="smarter__viz">
            <DutyCycle />
            <p className="smarter__caption">
              {ITEMS[open]?.caption ?? ITEMS[0].caption}
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
