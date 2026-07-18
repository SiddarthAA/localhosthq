import type { ReactNode } from 'react'

export default function Panel({
  title,
  icon,
  right,
  children,
  className = '',
  bodyClass = 'p-4',
}: {
  title: string
  icon?: ReactNode
  right?: ReactNode
  children: ReactNode
  className?: string
  bodyClass?: string
}) {
  return (
    <section className={`flex flex-col border border-border bg-card ${className}`}>
      <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          {icon}
          <h3 className="font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
            {title}
          </h3>
        </div>
        {right}
      </div>
      <div className={`flex-1 ${bodyClass}`}>{children}</div>
    </section>
  )
}
