import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, ShieldCheck } from 'lucide-react'
import { login } from '../lib/auth'
import ThreadLight from '../components/ThreadLight'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

const wide = { fontVariationSettings: '"wdth" 125' } as const

export default function Login() {
  const nav = useNavigate()
  const [email, setEmail] = useState('admin@ridewme.in')
  const [password, setPassword] = useState('password')
  const [error, setError] = useState('')
  const [signupNote, setSignupNote] = useState('')

  const onLogin = (e: FormEvent) => {
    e.preventDefault()
    setError('')
    if (login(email, password)) nav('/dashboard')
    else setError('Invalid credentials — use the demo account shown below.')
  }

  const onSignup = (e: FormEvent) => {
    e.preventDefault()
    setSignupNote('Sign-up is disabled in this demo. Use the Log in tab.')
  }

  return (
    <div className="relative min-h-svh w-full overflow-hidden bg-background font-sans text-foreground">
      <ThreadLight className="absolute inset-0 h-full w-full" />
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(60% 50% at 50% 40%, rgba(111,224,196,0.10), transparent 70%)',
        }}
      />
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          backgroundImage:
            'linear-gradient(var(--line) 1px, transparent 1px), linear-gradient(90deg, var(--line) 1px, transparent 1px)',
          backgroundSize: '64px 64px',
          maskImage:
            'radial-gradient(120% 90% at 50% 40%, #000 20%, transparent 75%)',
        }}
      />

      <div className="relative z-10 flex min-h-svh items-center justify-center p-6">
        <div className="w-full max-w-[420px]">
          <a href="/" className="mb-8 flex items-center justify-center gap-2.5">
            <img src="/logo.png" alt="" className="h-8 w-auto" />
            <span className="text-2xl font-bold tracking-tight" style={wide}>
              RidewMe
            </span>
          </a>

          <div className="border border-border bg-card/70 p-7 shadow-2xl backdrop-blur-xl">
            <div className="mb-6 text-center">
              <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-primary">
                Fleet console
              </p>
              <h1 className="mt-2 text-xl font-semibold" style={wide}>
                Sign in to your fleet
              </h1>
            </div>

            <Tabs defaultValue="login">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="login">Log in</TabsTrigger>
                <TabsTrigger value="signup">Sign up</TabsTrigger>
              </TabsList>

              <TabsContent value="login">
                <form onSubmit={onLogin} className="space-y-4 pt-5">
                  <div className="space-y-2">
                    <Label htmlFor="email">Work email</Label>
                    <Input
                      id="email"
                      type="email"
                      autoComplete="username"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="password">Password</Label>
                    <Input
                      id="password"
                      type="password"
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                    />
                  </div>
                  {error && (
                    <p className="text-sm text-destructive">{error}</p>
                  )}
                  <Button type="submit" className="w-full">
                    Sign in
                    <ArrowRight className="size-4" />
                  </Button>
                </form>
              </TabsContent>

              <TabsContent value="signup">
                <form onSubmit={onSignup} className="space-y-4 pt-5">
                  <div className="space-y-2">
                    <Label htmlFor="name">Full name</Label>
                    <Input id="name" type="text" placeholder="Jane Fleet" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="su-email">Work email</Label>
                    <Input id="su-email" type="email" placeholder="you@fleet.com" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="su-pw">Password</Label>
                    <Input id="su-pw" type="password" placeholder="••••••••" />
                  </div>
                  {signupNote && (
                    <p className="text-sm text-warning">{signupNote}</p>
                  )}
                  <Button type="submit" variant="secondary" className="w-full">
                    Create account
                  </Button>
                </form>
              </TabsContent>
            </Tabs>

            <div className="mt-6 flex items-center gap-2 border-t border-border pt-4">
              <ShieldCheck className="size-3.5 text-primary" />
              <p className="font-mono text-[11px] text-muted-foreground">
                DEMO · admin@ridewme.in · password
              </p>
            </div>
          </div>

          <a
            href="/"
            className="mt-6 block text-center font-mono text-xs text-muted-foreground transition-colors hover:text-foreground"
          >
            ← Back to site
          </a>
        </div>
      </div>
    </div>
  )
}
