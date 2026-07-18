import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { lazy, Suspense, type ReactNode } from 'react'
import Landing from './routes/Landing'
import { isAuthed } from './lib/auth'

// code-split the app views so the landing stays light (no recharts/shadcn)
const Login = lazy(() => import('./routes/Login'))
const Dashboard = lazy(() => import('./routes/Dashboard'))

function Fallback() {
  return (
    <div className="min-h-svh bg-background" style={{ background: '#0b0807' }} />
  )
}

function Protected({ children }: { children: ReactNode }) {
  return isAuthed() ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route
          path="/login"
          element={
            <Suspense fallback={<Fallback />}>
              <Login />
            </Suspense>
          }
        />
        <Route
          path="/dashboard"
          element={
            <Protected>
              <Suspense fallback={<Fallback />}>
                <Dashboard />
              </Suspense>
            </Protected>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
