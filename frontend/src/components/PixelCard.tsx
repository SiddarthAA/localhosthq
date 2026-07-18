import { useEffect, useRef, type ReactNode } from 'react'
import './PixelCard.css'

class Pixel {
  ctx: CanvasRenderingContext2D
  x: number
  y: number
  color: string
  speed: number
  size = 0
  sizeStep: number
  minSize = 0.5
  maxSize: number
  delay: number
  counter = 0
  counterStep: number
  isIdle = false
  isReverse = false
  isShimmer = false

  constructor(
    canvas: HTMLCanvasElement,
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    color: string,
    speed: number,
    delay: number,
  ) {
    this.ctx = ctx
    this.x = x
    this.y = y
    this.color = color
    this.speed = Math.random() * 0.8 * speed + 0.1
    this.sizeStep = Math.random() * 0.4
    this.maxSize = Math.random() * (2.6 - this.minSize) + this.minSize
    this.delay = delay
    this.counterStep = Math.random() * 4 + (canvas.width + canvas.height) * 0.008
  }

  private rect() {
    const c = this.size / 2
    this.ctx.fillStyle = this.color
    this.ctx.fillRect(this.x + c, this.y + c, this.size, this.size)
  }

  appear() {
    this.isIdle = false
    if (this.counter <= this.delay) {
      this.counter += this.counterStep
      return
    }
    if (this.size >= this.maxSize) this.isShimmer = true
    if (this.isShimmer) this.shimmer()
    else this.size += this.sizeStep
    this.rect()
  }

  disappear() {
    this.isShimmer = false
    this.counter = 0
    if (this.size <= 0) {
      this.isIdle = true
      return
    }
    this.size -= 0.1
    this.rect()
  }

  private shimmer() {
    if (this.size >= this.maxSize) this.isReverse = true
    else if (this.size <= this.minSize) this.isReverse = false
    this.size += this.isReverse ? -this.speed : this.speed
  }
}

type Props = {
  children: ReactNode
  className?: string
  colors?: string[]
  gap?: number
  speed?: number
}

export default function PixelCard({
  children,
  className = '',
  colors = ['#6fe0c4', '#38c9a4', '#f3eee3'],
  gap = 6,
  speed = 40,
}: Props) {
  const container = useRef<HTMLDivElement>(null)
  const canvas = useRef<HTMLCanvasElement>(null)
  const pixels = useRef<Pixel[]>([])
  const raf = useRef<number>(0)
  const last = useRef<number>(0)
  const mode = useRef<'appear' | 'disappear'>('disappear')

  useEffect(() => {
    const cv = canvas.current
    const box = container.current
    if (!cv || !box) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduce) return
    const ctx = cv.getContext('2d')
    if (!ctx) return

    const build = () => {
      const rect = box.getBoundingClientRect()
      const w = Math.floor(rect.width)
      const h = Math.floor(rect.height)
      cv.width = w
      cv.height = h
      cv.style.width = `${w}px`
      cv.style.height = `${h}px`
      const arr: Pixel[] = []
      for (let x = 0; x < w; x += gap) {
        for (let y = 0; y < h; y += gap) {
          const color = colors[Math.floor(Math.random() * colors.length)]
          const dist = Math.sqrt(x * x + y * y)
          arr.push(new Pixel(cv, ctx, x, y, color, speed * 0.001, dist))
        }
      }
      pixels.current = arr
    }

    const loop = (t: number) => {
      raf.current = requestAnimationFrame(loop)
      const interval = 1000 / 60
      if (t - last.current < interval) return
      last.current = t
      ctx.clearRect(0, 0, cv.width, cv.height)
      let allIdle = true
      for (const p of pixels.current) {
        p[mode.current]()
        if (!p.isIdle) allIdle = false
      }
      if (mode.current === 'disappear' && allIdle) {
        cancelAnimationFrame(raf.current)
        raf.current = 0
      }
    }

    const start = (m: 'appear' | 'disappear') => {
      mode.current = m
      if (!raf.current) raf.current = requestAnimationFrame(loop)
    }

    build()
    const onEnter = () => start('appear')
    const onLeave = () => start('disappear')
    box.addEventListener('mouseenter', onEnter)
    box.addEventListener('mouseleave', onLeave)
    box.addEventListener('focusin', onEnter)
    box.addEventListener('focusout', onLeave)
    const ro = new ResizeObserver(build)
    ro.observe(box)

    return () => {
      cancelAnimationFrame(raf.current)
      box.removeEventListener('mouseenter', onEnter)
      box.removeEventListener('mouseleave', onLeave)
      box.removeEventListener('focusin', onEnter)
      box.removeEventListener('focusout', onLeave)
      ro.disconnect()
    }
  }, [colors, gap, speed])

  return (
    <div ref={container} className={`pixelcard ${className}`}>
      <canvas ref={canvas} className="pixelcard__canvas" aria-hidden="true" />
      {children}
    </div>
  )
}
