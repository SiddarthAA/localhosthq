import { useEffect, useState } from 'react'
import { scrollTo } from '../lib/site'
import './BookPill.css'

/** Persistent floating CTA — the reference's always-present "Book the Flight". */
export default function BookPill() {
  const [hidden, setHidden] = useState(false)

  useEffect(() => {
    const target = document.querySelector('#contact')
    if (!target) return
    const io = new IntersectionObserver(
      ([entry]) => setHidden(entry.isIntersecting),
      { rootMargin: '0px 0px -30% 0px' },
    )
    io.observe(target)
    return () => io.disconnect()
  }, [])

  return (
    <div className={`bookpill${hidden ? ' bookpill--hidden' : ''}`}>
      <button
        className="bookpill__label"
        onClick={() => scrollTo('#contact')}
        type="button"
      >
        Book a demo
      </button>
      <button
        className="bookpill__icon"
        onClick={() => scrollTo('#contact')}
        type="button"
        aria-label="Book a demo"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M7 17 17 7M17 7H8M17 7v9"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
    </div>
  )
}
