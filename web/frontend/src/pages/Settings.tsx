import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, Eye, EyeOff, Loader2, AlertTriangle } from 'lucide-react'
import { api } from '../api'
import { useToast } from '../App'

export default function Settings() {
  const { addToast } = useToast()
  const [loading, setLoading]       = useState(true)
  const [saving, setSaving]         = useState(false)
  const [showKey, setShowKey]       = useState(false)
  const [apiKey, setApiKey]         = useState('')
  const [keyMissing, setKeyMissing] = useState(false)

  useEffect(() => {
    api.settings.get()
      .then((d) => { setApiKey(d.momentum_api_key); setKeyMissing(d.api_key_missing) })
      .catch(() => addToast('error', 'Failed to load settings'))
      .finally(() => setLoading(false))
  }, [addToast])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await api.settings.update({ momentum_api_key: apiKey })
      setKeyMissing(!apiKey.trim())
      addToast('success', 'Settings saved')
    } catch (err) {
      addToast('error', err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Link to="/" className="btn-ghost p-2" aria-label="Back to dashboard">
          <ArrowLeft size={15} />
        </Link>
        <h1 className="text-lg font-semibold text-slate-100">Settings</h1>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-24">
          <Loader2 size={24} className="animate-spin text-primary" />
        </div>
      ) : (
        <form onSubmit={handleSubmit} noValidate>
          <div className="card p-6 space-y-5">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest">
              Momentum Global Configuration
            </h2>

            {keyMissing && (
              <div className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg
                bg-amber-500/10 border border-amber-500/30 text-amber-300 text-sm">
                <AlertTriangle size={14} className="shrink-0" aria-hidden />
                No API key is set — Momentum sites will not run until this is configured.
              </div>
            )}

            <div>
              <label htmlFor="apiKey" className="form-label">API Key</label>
              <div className="relative">
                <input id="apiKey"
                  type={showKey ? 'text' : 'password'}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                  className="form-input pr-10 font-mono"
                  autoComplete="off" />
                <button type="button"
                  onClick={() => setShowKey((v) => !v)}
                  aria-label={showKey ? 'Hide API key' : 'Show API key'}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500
                    hover:text-slate-300 transition-colors p-1 rounded cursor-pointer">
                  {showKey ? <EyeOff size={14} aria-hidden /> : <Eye size={14} aria-hidden />}
                </button>
              </div>
              <p className="form-helper">
                Shared across all Momentum sites. Takes effect on the next queue run.
              </p>
            </div>

            <div className="flex gap-3 pt-1">
              <button type="submit" disabled={saving} className="btn-primary">
                {saving && <Loader2 size={13} className="animate-spin" aria-hidden />}
                {saving ? 'Saving…' : 'Save Settings'}
              </button>
              <Link to="/" className="btn-secondary">Cancel</Link>
            </div>
          </div>
        </form>
      )}
    </div>
  )
}
