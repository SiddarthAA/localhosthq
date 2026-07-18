import { useEffect, useState } from 'react'
import './BookPill.css'

/** Persistent floating CTA — routes to the dashboard (auth wired later). */
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
      <a className="bookpill__label" href="/dashboard">
        Login
      </a>
      <a className="bookpill__icon" href="/dashboard" aria-label="Login">
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
      </a>
    </div>
  )
}
