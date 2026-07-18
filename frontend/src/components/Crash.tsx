import Reveal from './Reveal'
import SectionHead from './SectionHead'
import SpecList, { type Spec } from './SpecList'
import './Crash.css'

const SENSORS = [
  { label: 'Accelerometer', reading: 'Δ 6.2 g', fill: 92 },
  { label: 'Gyroscope', reading: 'Δ 340 °/s', fill: 78 },
  { label: 'GPS', reading: 'Δ speed −48 km/h', fill: 84 },
]

const SPEC: Spec[] = [
  { k: 'Sensors fused', v: 'Accelerometer, gyroscope, GPS' },
  { k: 'Confirmation rule', v: '≥ 2 of 3 signals must agree' },
  { k: 'Severity classes', v: 'Minor, moderate, severe' },
  { k: 'Dispatch discipline', v: 'Driver-cancel countdown before authorities' },
  { k: 'False-positive guard', v: 'Gravity-compensated impact baseline' },
  { k: 'Fleet-manager alert', v: 'Instant' },
  { k: 'Works offline', v: 'Fully' },
]

export default function Crash() {
  return (
    <section
      id="crash"
      className="crash section on-dark"
      data-nav-theme="dark"
    >
      <div className="shell">
        <SectionHead
          eyebrow="Sensor-fusion crash detection"
          title="When impact happens, it knows — and it doesn’t overreact"
          intro="A second engine watches motion. It fuses three independent sensors and calls a crash only when they agree — then gives the driver a window to cancel before anyone is dispatched. Because a pothole isn’t an accident."
        />

        <div className="crash__grid">
          <Reveal className="crash__panel">
            <div className="crash__panel-head">
              <span className="u-label">Impact fusion</span>
              <span className="u-label crash__live">
                <span className="crash__live-dot" />
                Live
              </span>
            </div>
            <ul className="crash__sensors">
              {SENSORS.map((s) => (
                <li className="csensor" key={s.label}>
                  <div className="csensor__row">
                    <span className="csensor__label">{s.label}</span>
                    <span className="csensor__reading">{s.reading}</span>
                  </div>
                  <div className="csensor__track">
                    <span
                      className="csensor__fill"
                      style={{ width: `${s.fill}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
            <div className="crash__verdict">
              <span className="crash__verdict-dot" />
              <span className="crash__verdict-label">Crash · severe</span>
              <span className="crash__verdict-meta">3 / 3 agree · 8s to cancel</span>
            </div>
          </Reveal>

          <div className="crash__spec">
            <SpecList items={SPEC} />
          </div>
        </div>
      </div>
    </section>
  )
}
