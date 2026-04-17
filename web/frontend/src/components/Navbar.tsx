import { Link, useLocation } from 'react-router-dom'
import { Settings } from 'lucide-react'

export default function Navbar() {
  const { pathname } = useLocation()

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-bg-surface/80 backdrop-blur-md">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">

        <Link to="/" className="flex items-center gap-2.5 group" aria-label="QueuePilot home">
          <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center shadow-lg shadow-primary/30">
            <svg viewBox="0 0 16 16" fill="none" className="w-4 h-4" aria-hidden="true">
              <path d="M2 4h12M2 8h8M2 12h5" stroke="white" strokeWidth="1.8" strokeLinecap="round"/>
              <circle cx="13" cy="11" r="2.2" fill="white"/>
            </svg>
          </div>
          <span className="font-semibold text-slate-100 text-sm tracking-wide group-hover:text-white transition-colors">
            QueuePilot
          </span>
        </Link>

        <Link
          to="/settings"
          className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg transition-colors duration-150
            ${pathname === '/settings'
              ? 'text-slate-200 bg-bg-hover'
              : 'text-slate-400 hover:text-slate-200 hover:bg-bg-hover'
            }`}
        >
          <Settings size={14} aria-hidden />
          Settings
        </Link>

      </div>
    </header>
  )
}
