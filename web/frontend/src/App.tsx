import { createContext, useContext, useState, useCallback } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react'
import type { Toast } from './types'
import Navbar from './components/Navbar'
import Dashboard from './pages/Dashboard'
import SiteForm from './pages/SiteForm'
import Settings from './pages/Settings'

// ── Toast context ──────────────────────────────────────────────────────────────

interface ToastCtx { addToast: (type: Toast['type'], message: string) => void }
export const ToastContext = createContext<ToastCtx>({ addToast: () => {} })
export const useToast = () => useContext(ToastContext)

const ICONS = { success: CheckCircle, error: XCircle, warning: AlertTriangle, info: Info }
const STYLES = {
  success: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  error:   'border-red-500/30 bg-red-500/10 text-red-300',
  warning: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
  info:    'border-blue-500/30 bg-blue-500/10 text-blue-300',
}

function ToastList({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: string) => void }) {
  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 pointer-events-none">
      {toasts.map((t) => {
        const Icon = ICONS[t.type]
        return (
          <div
            key={t.id}
            role="alert"
            aria-live="polite"
            className={`flex items-center gap-3 px-4 py-3 rounded-xl border backdrop-blur-sm
              shadow-2xl max-w-sm pointer-events-auto ${STYLES[t.type]}`}
          >
            <Icon size={15} className="shrink-0" aria-hidden />
            <span className="text-sm font-medium flex-1">{t.message}</span>
            <button
              onClick={() => onDismiss(t.id)}
              aria-label="Dismiss notification"
              className="shrink-0 opacity-60 hover:opacity-100 transition-opacity cursor-pointer"
            >
              <X size={13} />
            </button>
          </div>
        )
      })}
    </div>
  )
}

export default function App() {
  const [toasts, setToasts] = useState<Toast[]>([])

  const addToast = useCallback((type: Toast['type'], message: string) => {
    const id = Math.random().toString(36).slice(2)
    setToasts((p) => [...p, { id, type, message }])
    setTimeout(() => setToasts((p) => p.filter((t) => t.id !== id)), 4500)
  }, [])

  const dismiss = useCallback((id: string) => setToasts((p) => p.filter((t) => t.id !== id)), [])

  return (
    <ToastContext.Provider value={{ addToast }}>
      <BrowserRouter>
        <div className="min-h-screen bg-bg-base">
          <Navbar />
          <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
            <Routes>
              <Route path="/"                     element={<Dashboard />} />
              <Route path="/sites/add"            element={<SiteForm />} />
              <Route path="/sites/:urlName/edit"  element={<SiteForm />} />
              <Route path="/settings"             element={<Settings />} />
            </Routes>
          </main>
        </div>
        <ToastList toasts={toasts} onDismiss={dismiss} />
      </BrowserRouter>
    </ToastContext.Provider>
  )
}
