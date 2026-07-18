import { useNavigate } from 'react-router-dom'
import { LogOut, Wifi, WifiOff } from 'lucide-react'
import { logout } from '@/lib/auth'
import { useLive } from '@/lib/useLive'
import { Button } from '@/components/ui/button'

const wide = { fontVariationSettings: '"wdth" 122' } as const

export default function TopBar() {
  const nav = useNavigate()
  const d = useLive()
  const online = d.online && d.link !== 'offline'

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/80 backdrop-blur-xl">
      <div className="mx-auto flex h-14 max-w-[1600px] items-center gap-4 px-4 sm:px-6">
        <a href="/" className="flex items-center gap-2">
          <img src="/logo.png" alt="" className="h-6 w-auto" />
          <span className="text-lg font-bold tracking-tight" style={wide}>
            RidewMe
          </span>
        </a>
        <span className="hidden font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground sm:inline">
          / Fleet console
        </span>

        <div className="ml-auto flex items-center gap-2 sm:gap-4">
          <div className="hidden items-center gap-2 border border-border px-2.5 py-1 md:flex">
            {online ? (
              <Wifi className="size-3.5 text-primary" />
            ) : (
              <WifiOff className="size-3.5 text-destructive" />
            )}
            <span className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {d.link}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="relative flex size-2">
              <span className={`absolute inline-flex size-full animate-ping rounded-full ${online ? 'bg-primary' : 'bg-destructive'} opacity-60`} />
              <span className={`relative inline-flex size-2 rounded-full ${online ? 'bg-primary' : 'bg-destructive'}`} />
            </span>
            <div className="leading-tight">
              <p className="text-sm font-semibold">{d.name}</p>
              <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                {d.driver_id}
              </p>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={() => { logout(); nav('/login') }}>
            <LogOut className="size-4" />
            <span className="hidden sm:inline">Sign out</span>
          </Button>
        </div>
      </div>
    </header>
  )
}
