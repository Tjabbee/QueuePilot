import { useState, useEffect } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { ArrowLeft, Eye, EyeOff, Loader2, Info } from 'lucide-react'
import { api } from '../api'
import { useToast } from '../App'
import type { SiteFormData } from '../types'

const SYSTEM_TYPES = [
  { value: 'momentum', label: 'Momentum' },
  { value: 'vitec',    label: 'Vitec Arena' },
]

const EMPTY: SiteFormData = {
  url_name: '', fullname: '', system_type: 'momentum',
  momentum_id: '', base_url: '', username: '', password: '', active: true,
}

export default function SiteForm() {
  const { urlName } = useParams<{ urlName: string }>()
  const navigate = useNavigate()
  const { addToast } = useToast()
  const isEdit = !!urlName

  const [form, setForm]         = useState<SiteFormData>(EMPTY)
  const [loading, setLoading]   = useState(isEdit)
  const [saving, setSaving]     = useState(false)
  const [showPass, setShowPass] = useState(false)

  useEffect(() => {
    if (!isEdit || !urlName) return
    api.sites.get(urlName)
      .then((s) => setForm({
        url_name: s.url_name, fullname: s.fullname,
        system_type: s.system_type, momentum_id: s.momentum_id ?? '',
        base_url: s.base_url ?? '', username: s.username ?? '',
        password: '', active: s.active,
      }))
      .catch(() => { addToast('error', 'Site not found'); navigate('/') })
      .finally(() => setLoading(false))
  }, [isEdit, urlName, navigate, addToast])

  const set = <K extends keyof SiteFormData>(k: K, v: SiteFormData[K]) =>
    setForm((p) => ({ ...p, [k]: v }))

  const urlPreview = form.system_type === 'momentum'
    ? `https://${form.url_name || 'slug'}-fastighet.momentum.se/Prod/${form.momentum_id || 'ID'}/PmApi/v2`
    : null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (isEdit && urlName) {
        await api.sites.update(urlName, form)
        addToast('success', 'Site updated')
      } else {
        await api.sites.create(form)
        addToast('success', `Site '${form.url_name}' added`)
      }
      navigate('/')
    } catch (err) {
      addToast('error', err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center py-24">
      <Loader2 size={24} className="animate-spin text-primary" />
    </div>
  )

  return (
    <div className="max-w-xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Link to="/" className="btn-ghost p-2" aria-label="Back">
          <ArrowLeft size={15} />
        </Link>
        <div>
          <h1 className="text-lg font-semibold text-slate-100">
            {isEdit ? 'Edit Site' : 'Add Site'}
          </h1>
          {isEdit && <p className="text-xs text-slate-500 font-mono mt-0.5">{urlName}</p>}
        </div>
      </div>

      <form onSubmit={handleSubmit} noValidate className="space-y-5">
        {/* Site config card */}
        <div className="card p-6 space-y-4">
          <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest">
            Site Configuration
          </h2>

          {/* System type */}
          <div>
            <label htmlFor="system_type" className="form-label">System / Platform</label>
            <select id="system_type" value={form.system_type}
              onChange={(e) => set('system_type', e.target.value)}
              className="form-select">
              {SYSTEM_TYPES.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
            <p className="form-helper">The platform used by this housing community.</p>
          </div>

          {/* Site ID */}
          <div>
            <label htmlFor="url_name" className="form-label">
              Site ID <span className="text-red-400">*</span>
            </label>
            {isEdit ? (
              <input id="url_name" type="text" value={form.url_name}
                disabled className="form-input opacity-50 cursor-not-allowed" />
            ) : (
              <input id="url_name" type="text" required
                value={form.url_name}
                onChange={(e) => set('url_name', e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ''))}
                placeholder="kbab"
                className="form-input" />
            )}
            <p className="form-helper">
              {isEdit ? 'Site ID cannot be changed after creation.' :
               form.system_type === 'momentum'
                 ? <>Lowercase slug — used as subdomain prefix (<code>kbab</code> → <code>kbab-fastighet.momentum.se</code>)</>
                 : 'Lowercase identifier for this site.'}
            </p>
          </div>

          {/* Display name */}
          <div>
            <label htmlFor="fullname" className="form-label">
              Display Name <span className="text-red-400">*</span>
            </label>
            <input id="fullname" type="text" required
              value={form.fullname}
              onChange={(e) => set('fullname', e.target.value)}
              placeholder="KBAB — Karlstads Bostads AB"
              className="form-input" />
            <p className="form-helper">Human-readable name shown in the dashboard.</p>
          </div>

          {/* Momentum fields */}
          {form.system_type === 'momentum' && (
            <>
              <div>
                <label htmlFor="momentum_id" className="form-label">
                  Momentum ID
                  <span className="ml-2 font-normal text-slate-500 text-xs">path segment in API URL</span>
                </label>
                <input id="momentum_id" type="text"
                  value={form.momentum_id}
                  onChange={(e) => set('momentum_id', e.target.value)}
                  placeholder="Kar"
                  className="form-input" />
                {urlPreview && (
                  <p className="form-helper">
                    API URL: <code>{urlPreview}</code>
                  </p>
                )}
              </div>
              <div className="flex items-start gap-2.5 px-3 py-2.5 rounded-lg bg-bg-elevated border border-border text-xs text-slate-400">
                <Info size={13} className="shrink-0 mt-0.5 text-primary" aria-hidden />
                <span>
                  The Momentum API key is shared across all sites and configured in{' '}
                  <Link to="/settings" className="text-primary hover:text-primary-light underline">
                    Settings
                  </Link>.
                </span>
              </div>
            </>
          )}

          {/* Vitec fields */}
          {form.system_type === 'vitec' && (
            <div>
              <label htmlFor="base_url" className="form-label">Base URL</label>
              <input id="base_url" type="url"
                value={form.base_url}
                onChange={(e) => set('base_url', e.target.value)}
                placeholder="https://minasidor.vatterhem.se"
                className="form-input" />
              <p className="form-helper">The Vitec Arena site root URL.</p>
            </div>
          )}
        </div>

        {/* Credentials card */}
        <div className="card p-6 space-y-4">
          <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest">
            Credentials
          </h2>

          <div>
            <label htmlFor="username" className="form-label">
              Username / Personnummer <span className="text-red-400">*</span>
            </label>
            <input id="username" type="text" required
              value={form.username}
              onChange={(e) => set('username', e.target.value)}
              placeholder="YYYYMMDD-XXXX"
              className="form-input font-mono"
              autoComplete="username" />
          </div>

          <div>
            <label htmlFor="password" className="form-label">
              Password {!isEdit && <span className="text-red-400">*</span>}
            </label>
            <div className="relative">
              <input id="password" type={showPass ? 'text' : 'password'}
                required={!isEdit}
                value={form.password}
                onChange={(e) => set('password', e.target.value)}
                placeholder={isEdit ? 'Leave blank to keep current password' : 'Enter password'}
                className="form-input pr-10"
                autoComplete={isEdit ? 'new-password' : 'current-password'} />
              <button type="button"
                onClick={() => setShowPass((v) => !v)}
                aria-label={showPass ? 'Hide password' : 'Show password'}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500
                  hover:text-slate-300 transition-colors p-1 rounded cursor-pointer">
                {showPass ? <EyeOff size={14} aria-hidden /> : <Eye size={14} aria-hidden />}
              </button>
            </div>
            {isEdit && <p className="form-helper">Leave blank to keep the existing password.</p>}
          </div>

          {/* Active toggle */}
          <div className="flex items-center justify-between py-1">
            <div>
              <p className="text-sm font-medium text-slate-300">Active</p>
              <p className="text-xs text-slate-500 mt-0.5">Inactive sites are skipped during queue updates.</p>
            </div>
            <button type="button" role="switch" aria-checked={form.active}
              onClick={() => set('active', !form.active)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full
                transition-colors duration-200 focus:outline-none focus:ring-2
                focus:ring-primary focus:ring-offset-2 focus:ring-offset-bg-surface
                cursor-pointer ${form.active ? 'bg-primary' : 'bg-slate-700'}`}>
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-sm
                transition-transform duration-200 ${form.active ? 'translate-x-6' : 'translate-x-1'}`} />
            </button>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button type="submit" disabled={saving} className="btn-primary">
            {saving && <Loader2 size={13} className="animate-spin" aria-hidden />}
            {saving ? 'Saving…' : isEdit ? 'Save Changes' : 'Add Site'}
          </button>
          <Link to="/" className="btn-secondary">Cancel</Link>
        </div>
      </form>
    </div>
  )
}
