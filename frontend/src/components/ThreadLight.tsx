import { useEffect, useRef } from 'react'

/** Animated flowing "thread light" background (canvas).
    Approximates the 21st.dev thread-light aesthetic — teal light threads
    undulating over a dark field. */
export default function ThreadLight({ className }: { className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    let w = 0
    let h = 0
    let dpr = 1
    const resize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      w = canvas.clientWidth
      h = canvas.clientHeight
      canvas.width = Math.floor(w * dpr)
      canvas.height = Math.floor(h * dpr)
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(canvas)

    const LINES = 40
    let t = 0
    let raf = 0

    const render = () => {
      ctx.clearRect(0, 0, w, h)
      const cx = w * 0.5
      for (let i = 0; i < LINES; i++) {
        const p = i / (LINES - 1)
        const baseY = p * h
        ctx.beginPath()
        for (let x = 0; x <= w; x += 8) {
          const dx = (x - cx) / w
          // amplitude swells toward the centre — the "light" focus
          const focus = Math.exp(-(dx * dx) * 5)
          const amp = (10 + focus * 46) * (0.5 + 0.5 * Math.sin(i * 0.4))
          const y =
            baseY +
            Math.sin(x * 0.006 + t * 0.6 + i * 0.35) * amp +
            Math.sin(x * 0.013 - t * 0.4 + i * 0.9) * amp * 0.4
          if (x === 0) ctx.moveTo(x, y)
          else ctx.lineTo(x, y)
        }
        const shimmer = 0.04 + 0.06 * (0.5 + 0.5 * Math.sin(t * 0.8 + i * 0.6))
        ctx.strokeStyle = `rgba(111, 224, 196, ${shimmer})`
        ctx.lineWidth = 1
        ctx.stroke()
      }
      t += 0.016
      raf = requestAnimationFrame(render)
    }

    if (reduce) {
      render() // one static frame
    } else {
      raf = requestAnimationFrame(render)
    }

    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
    }
  }, [])

  return <canvas ref={ref} className={className} aria-hidden="true" />
}
