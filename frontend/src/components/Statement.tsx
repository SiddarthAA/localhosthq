import { useEffect, useRef } from 'react'
import { gsap, prefersReducedMotion } from '../lib/gsap'
import './Statement.css'

const TEXT =
  'RidewMe is a complete safety engine that rides along inside the vehicle — ' +
  'reading fatigue and detecting crashes in real time, deciding with the ' +
  'judgment of a co-pilot, and reporting only what matters. On hardware you ' +
  'already own. With video that never leaves the cab.'

export default function Statement() {
  const root = useRef<HTMLElement>(null)

  useEffect(() => {
    if (prefersReducedMotion() || !root.current) return
    const ctx = gsap.context(() => {
      gsap.to('.statement__w', {
        opacity: 1,
        ease: 'none',
        stagger: 0.4,
        scrollTrigger: {
          trigger: '.statement__body',
          start: 'top 80%',
          end: 'bottom 62%',
          scrub: true,
        },
      })
    }, root)
    return () => ctx.revert()
  }, [])

  const words = TEXT.split(' ')

  return (
    <section
      id="intro"
      className="statement section on-light"
      data-nav-theme="light"
      ref={root}
    >
      <div className="shell">
        <p className="statement__body">
          {words.map((w, i) => (
            <span className="statement__w" key={i}>
              {w}{' '}
            </span>
          ))}
        </p>
      </div>
    </section>
  )
}
