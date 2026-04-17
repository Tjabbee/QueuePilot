import { useState, useEffect, useCallback, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  Plus, Play, ChevronDown, Pencil, Trash2, Loader2,
  AlertTriangle, Inbox, RefreshCw, Clock, ArrowUpDown,
  ArrowUp, ArrowDown, XCircle, Search, X,
} from 'lucide-react'
import { api } from '../api'
import { useToast } from '../App'
import type { Site, SitesResponse, ContainerStatus } from '../types'

// ── Sub-components ─────────────────────────────────────────────────────────

function RunnerDot({ status }: { status: string }) {
  if (status === 'running') return (
    <span className="relative flex h-2.5 w-2.5">
      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
    </span>
  )
  if (status === 'not_found' || status === 'error') return (
    <span className="h-2.5 w-2.5 rounded-full bg-amber-500 block" />
  )
  return <span className="h-2.5 w-2.5 rounded-full bg-slate-600 block" />
}

function SystemBadge({ type }: { type: string }) {
  if (type === 'momentum') return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium
      bg-teal-500/15 text-teal-400 border border-teal-500/20 whitespace-nowrap">
      Momentum
    </span>
  )
  if (type === 'vitec') return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium
      bg-indigo-500/15 text-indigo-400 border border-indigo-500/20 whitespace-nowrap">
      Vitec Arena
    </span>
  )
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium
      bg-slate-500/15 text-slate-400 border border-slate-500/20 whitespace-nowrap">
      {type}
    </span>
  )
}

type SortCol = 'fullname' | 'system_type' | 'last_login' | 'queue_points' | null

function SortBtn({ col, current, asc }: { col: SortCol; current: SortCol; asc: boolean }) {
  if (current !== col) return <ArrowUpDown size={11} className="text-slate-600 ml-1 inline" />
  return asc
    ? <ArrowUp size={11} className="text-primary ml-1 inline" />
    : <ArrowDown size={11} className="text-primary ml-1 inline" />
}

// ── Delete confirmation modal ──────────────────────────────────────────────

function DeleteModal({ urlName, onConfirm, onCancel }: {
  urlName: string; onConfirm: () => void; onCancel: () => void
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog" aria-modal="true" aria-labelledby="del-title"
    >
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onCancel} />
      <div className="relative card p-6 max-w-sm w-full shadow-2xl">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-red-500/15 flex items-center justify-center shrink-0">
            <Trash2 size={17} className="text-red-400" />
          </div>
          <div>
            <h2 id="del-title" className="text-sm font-semibold text-slate-100">Delete site</h2>
            <p className="text-xs text-slate-500 mt-0.5">This action cannot be undone</p>
          </div>
        </div>
        <p className="text-sm text-slate-300 mb-6">
          Delete <code>{urlName}</code> and all its credentials?
        </p>
        <div className="flex gap-3 justify-end">
          <button onClick={onCancel} className="btn-secondary">Cancel</button>
          <button
            onClick={onConfirm}
            className="btn-primary !bg-red-600 hover:!bg-red-700 focus:!ring-red-500"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Site row ──────────────────────────────────────────────────────────────

function SiteRow({
  site, expanded, onToggleExpand, onToggleActive, onDeleteRequest, isDeleting,
}: {
  site: Site
  expanded: boolean
  onToggleExpand: () => void
  onToggleActive: () => void
  onDeleteRequest: () => void
  isDeleting: boolean
}) {
  const hasDetails = site.queue_details.length > 1

  return (
    <>
      <tr
        className={`group transition-colors duration-100
          ${hasDetails ? 'cursor-pointer hover:bg-bg-elevated' : 'hover:bg-bg-surface/60'}
          ${!site.active ? 'opacity-40' : ''}`}
        onClick={hasDetails ? onToggleExpand : undefined}
      >
        {/* expand indicator */}
        <td className="px-4 py-3.5 w-8">
          {hasDetails
            ? <ChevronDown size={13} className={`text-slate-500 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`} />
            : <span className="block w-3.5" />
          }
        </td>

        {/* site name + id */}
        <td className="px-3 py-3.5 max-w-[190px]">
          <div className="font-medium text-slate-200 text-sm truncate">{site.fullname}</div>
          <div className="text-xs text-slate-500 font-mono mt-0.5 truncate">{site.url_name}</div>
          {site.system_type === 'momentum' && !site.momentum_id && (
            <Link
              to={`/sites/${site.url_name}/edit`}
              onClick={(e) => e.stopPropagation()}
              className="inline-flex items-center gap-1 mt-1 text-xs text-amber-400 hover:text-amber-300"
            >
              <AlertTriangle size={10} aria-hidden /> Missing ID
            </Link>
          )}
        </td>

        {/* system */}
        <td className="px-3 py-3.5"><SystemBadge type={site.system_type} /></td>

        {/* username */}
        <td className="px-3 py-3.5 max-w-[150px]">
          {site.username
            ? <span className="text-sm text-slate-300 font-mono truncate block" title={site.username}>{site.username}</span>
            : <span className="text-slate-600">—</span>
          }
        </td>

        {/* last login */}
        <td className="px-3 py-3.5">
          {site.last_login
            ? <span className="text-xs font-mono text-slate-400 whitespace-nowrap">{site.last_login}</span>
            : <span className="text-slate-600 text-sm">Never</span>
          }
        </td>

        {/* points */}
        <td className="px-3 py-3.5">
          {site.queue_points != null
            ? <span className="text-sm font-mono font-semibold text-primary-light">{site.queue_points.toLocaleString()}</span>
            : <span className="text-slate-600">—</span>
          }
        </td>

        {/* active toggle */}
        <td className="px-3 py-3.5" onClick={(e) => e.stopPropagation()}>
          <button
            role="switch"
            aria-checked={site.active}
            aria-label={`${site.active ? 'Deactivate' : 'Activate'} ${site.fullname}`}
            onClick={onToggleActive}
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors duration-200
              focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-bg-surface
              cursor-pointer ${site.active ? 'bg-primary' : 'bg-slate-700'}`}
          >
            <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow-sm transition-transform duration-200
              ${site.active ? 'translate-x-4' : 'translate-x-1'}`} />
          </button>
        </td>

        {/* actions */}
        <td className="px-4 py-3.5 text-right" onClick={(e) => e.stopPropagation()}>
          <div className="flex items-center justify-end gap-1">
            <Link
              to={`/sites/${site.url_name}/edit`}
              className="btn-ghost py-1 px-2"
              aria-label={`Edit ${site.fullname}`}
            >
              <Pencil size={12} aria-hidden />
              <span className="hidden sm:inline text-xs">Edit</span>
            </Link>
            <button
              onClick={onDeleteRequest}
              disabled={isDeleting}
              className="btn-danger py-1 px-2"
              aria-label={`Delete ${site.fullname}`}
            >
              {isDeleting
                ? <Loader2 size={12} className="animate-spin" aria-hidden />
                : <Trash2 size={12} aria-hidden />
              }
              <span className="hidden sm:inline text-xs">Delete</span>
            </button>
          </div>
        </td>
      </tr>

      {/* expanded details */}
      {hasDetails && expanded && (
        <tr className="bg-bg-elevated/40">
          <td colSpan={8} className="px-10 py-4">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
              Queue Breakdown
            </p>
            <table className="w-full max-w-sm">
              <thead>
                <tr className="text-xs text-slate-500">
                  <th className="text-left font-medium pb-2">Queue</th>
                  <th className="text-right font-medium pb-2">Points</th>
                  <th className="text-left font-medium pb-2 pl-4">Unit</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {site.queue_details.map((q, i) => (
                  <tr key={i}>
                    <td className="text-sm text-slate-300 py-1.5">{q.name}</td>
                    <td className="text-sm font-mono text-right text-primary-light py-1.5 tabular-nums">
                      {q.points.toLocaleString()}
                    </td>
                    <td className="text-xs text-slate-500 pl-4 py-1.5">{q.unit}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </td>
        </tr>
      )}
    </>
  )
}

// ── Skeleton ──────────────────────────────────────────────────────────────

function Skeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="card h-20" />
      <div className="flex gap-3">
        <div className="h-9 w-16 rounded-lg bg-bg-elevated" />
        <div className="h-9 w-52 rounded-lg bg-bg-elevated" />
        <div className="ml-auto h-9 w-28 rounded-lg bg-bg-elevated" />
      </div>
      <div className="card overflow-hidden">
        <div className="h-10 bg-bg-elevated" />
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-14 border-t border-border flex items-center gap-4 px-5">
            <div className="h-4 w-36 rounded bg-bg-elevated" />
            <div className="h-5 w-20 rounded-full bg-bg-elevated" />
            <div className="h-4 w-28 rounded bg-bg-elevated ml-auto" />
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Dashboard ─────────────────────────────────────────────────────────────

const SYSTEM_LABEL: Record<string, string> = { momentum: 'Momentum', vitec: 'Vitec Arena' }

export default function Dashboard() {
  const { addToast } = useToast()
  const [data, setData]                     = useState<SitesResponse | null>(null)
  const [status, setStatus]                 = useState<ContainerStatus | null>(null)
  const [loading, setLoading]               = useState(true)
  const [runBusy, setRunBusy]               = useState(false)
  const [loadErr, setLoadErr]               = useState<string | null>(null)
  const [filter, setFilter]                 = useState('all')
  const [search, setSearch]                 = useState('')
  const [showInactive, setShowInactive]     = useState(() => localStorage.getItem('showInactive') === 'true')
  const [expanded, setExpanded]             = useState<Set<string>>(new Set())
  const [sortCol, setSortCol]               = useState<SortCol>(() => (localStorage.getItem('sortCol') as SortCol) ?? null)
  const [sortAsc, setSortAsc]               = useState(() => localStorage.getItem('sortAsc') !== 'false')
  const [page, setPage]                     = useState(0)
  const [deletingId, setDeletingId]         = useState<string | null>(null)
  const [confirmDel, setConfirmDel]         = useState<string | null>(null)

  const PAGE_SIZE = 10

  const loadAll = useCallback(async () => {
    try {
      const [sites, st] = await Promise.all([api.sites.list(), api.status()])
      setData(sites)
      setStatus(st)
      setLoadErr(null)
    } catch (e) {
      setLoadErr(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadAll() }, [loadAll])

  // Poll while running
  useEffect(() => {
    if (status?.container_status !== 'running') return
    const t = setInterval(async () => {
      try {
        const s = await api.status()
        setStatus(s)
        if (s.container_status !== 'running') loadAll()
      } catch { /* ignore */ }
    }, 2000)
    return () => clearInterval(t)
  }, [status?.container_status, loadAll])

  const handleRun = async () => {
    setRunBusy(true)
    try {
      const res = await api.run()
      addToast(res.ok ? 'success' : 'warning', res.message)
      if (res.ok) setStatus(await api.status())
    } catch (e) {
      addToast('error', e instanceof Error ? e.message : 'Failed to start')
    } finally {
      setRunBusy(false)
    }
  }

  const handleToggle = async (urlName: string, current: boolean) => {
    setData((p) => p ? { ...p, sites: p.sites.map((s) => s.url_name === urlName ? { ...s, active: !current } : s) } : p)
    try {
      await api.sites.toggleActive(urlName)
    } catch {
      setData((p) => p ? { ...p, sites: p.sites.map((s) => s.url_name === urlName ? { ...s, active: current } : s) } : p)
      addToast('error', 'Failed to update status')
    }
  }

  const handleDelete = async (urlName: string) => {
    setDeletingId(urlName)
    setConfirmDel(null)
    try {
      await api.sites.delete(urlName)
      setData((p) => p ? { ...p, sites: p.sites.filter((s) => s.url_name !== urlName) } : p)
      addToast('success', `Site '${urlName}' deleted`)
    } catch (e) {
      addToast('error', e instanceof Error ? e.message : 'Failed to delete')
    } finally {
      setDeletingId(null)
    }
  }

  const toggleExpand = (id: string) =>
    setExpanded((p) => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n })

  const handleSort = (col: SortCol) => {
    let newCol: SortCol
    let newAsc: boolean
    if (sortCol !== col) {
      newCol = col; newAsc = true               // 1st click: sort asc
    } else if (sortAsc) {
      newCol = col; newAsc = false              // 2nd click: sort desc
    } else {
      newCol = null; newAsc = true              // 3rd click: reset
    }
    setSortCol(newCol)
    setSortAsc(newAsc)
    setPage(0)
    localStorage.setItem('sortCol', newCol ?? '')
    localStorage.setItem('sortAsc', String(newAsc))
  }

  const allTypes = useMemo(() =>
    [...new Set((data?.sites ?? []).map((s) => s.system_type))].sort(), [data])

  const filtered = useMemo(() => {
    let sites = data?.sites ?? []
    if (filter !== 'all') sites = sites.filter((s) => s.system_type === filter)
    if (!showInactive) sites = sites.filter((s) => s.active)
    if (search.trim()) {
      const q = search.trim().toLowerCase()
      const SYSTEM_MAP: Record<string, string> = { momentum: 'momentum', vitec: 'vitec arena' }
      sites = sites.filter((s) => [
        s.fullname, s.url_name, s.username,
        SYSTEM_MAP[s.system_type] ?? s.system_type,
        s.last_login, s.queue_points?.toString(),
        ...s.queue_details.map((d) => `${d.name} ${d.points} ${d.unit}`),
      ].some((v) => v?.toLowerCase().includes(q)))
    }
    if (sortCol) {
      sites = [...sites].sort((a, b) => {
        const av = sortCol === 'queue_points' ? (a.queue_points ?? -1)
          : sortCol === 'last_login' ? (a.last_login ?? '')
          : sortCol === 'system_type' ? a.system_type
          : a.fullname.toLowerCase()
        const bv = sortCol === 'queue_points' ? (b.queue_points ?? -1)
          : sortCol === 'last_login' ? (b.last_login ?? '')
          : sortCol === 'system_type' ? b.system_type
          : b.fullname.toLowerCase()
        if (av < bv) return sortAsc ? -1 : 1
        if (av > bv) return sortAsc ? 1 : -1
        return 0
      })
    }
    return sites
  }, [data, filter, showInactive, search, sortCol, sortAsc])

  // Reset to page 0 when filter, search, or show-inactive changes
  useEffect(() => { setPage(0) }, [filter, showInactive, search])

  const totalPages  = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const safePage    = Math.min(page, totalPages - 1)
  const pageSlice   = filtered.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE)
  const pageStart   = safePage * PAGE_SIZE + 1
  const pageEnd     = Math.min((safePage + 1) * PAGE_SIZE, filtered.length)

  if (loading) return <Skeleton />

  if (loadErr) return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <XCircle size={38} className="text-red-400 mb-4" aria-hidden />
      <p className="text-slate-300 font-medium mb-1">Failed to load data</p>
      <p className="text-slate-500 text-sm mb-6">{loadErr}</p>
      <button onClick={loadAll} className="btn-secondary">
        <RefreshCw size={13} aria-hidden /> Retry
      </button>
    </div>
  )

  const isRunning = status?.container_status === 'running'

  return (
    <div className="space-y-5">
      {/* API key warning */}
      {data?.api_key_missing && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-amber-500/30
          bg-amber-500/10 text-amber-300 text-sm">
          <AlertTriangle size={15} className="shrink-0" aria-hidden />
          <span>
            Momentum API key is missing — Momentum sites will not run.{' '}
            <Link to="/settings" className="underline underline-offset-2 hover:text-amber-200">
              Go to Settings
            </Link>
          </span>
        </div>
      )}

      {/* Runner status card */}
      <div className="card px-5 py-4 flex flex-wrap items-center gap-5 justify-between">
        <div className="flex items-center gap-5">
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-2">
              Runner
            </p>
            <div className="flex items-center gap-2">
              <RunnerDot status={status?.container_status ?? 'unknown'} />
              <span className="text-sm font-medium text-slate-200">
                {status?.container_status === 'exited'    ? 'Idle'
                 : status?.container_status === 'not_found' ? 'Not created'
                 : status?.container_status === 'running' ? 'Running'
                 : (status?.container_status ?? 'Unknown')}
              </span>
            </div>
          </div>
          {status?.finished_at && (
            <div className="pl-5 border-l border-border">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-2">
                Last Run
              </p>
              <div className="flex items-center gap-1.5">
                <Clock size={11} className="text-slate-500" aria-hidden />
                <span className="text-xs font-mono text-slate-400">{status.finished_at}</span>
              </div>
            </div>
          )}
        </div>

        <button onClick={handleRun} disabled={isRunning || runBusy} className="btn-primary">
          {isRunning || runBusy
            ? <><Loader2 size={13} className="animate-spin" aria-hidden /> Running…</>
            : <><Play size={13} aria-hidden /> Run Now</>
          }
        </button>
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3 justify-between">
        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="text-base font-semibold text-slate-100">
            Sites
            <span className="ml-2 text-sm font-normal text-slate-500">({filtered.length})</span>
            {filtered.length > PAGE_SIZE && (
              <span className="ml-1 text-xs font-normal text-slate-600">
                · page {safePage + 1}/{totalPages}
              </span>
            )}
          </h1>

          {allTypes.length > 1 && (
            <div className="flex items-center gap-1 bg-bg-elevated border border-border rounded-lg p-1">
              {(['all', ...allTypes]).map((sys) => (
                <button
                  key={sys}
                  onClick={() => setFilter(sys)}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition-all duration-150 cursor-pointer
                    ${filter === sys
                      ? 'bg-primary text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-bg-hover'}`}
                >
                  {sys === 'all' ? 'All' : (SYSTEM_LABEL[sys] ?? sys)}
                  {data?.totals[sys] != null && (
                    <span className={`ml-1.5 font-mono ${filter === sys ? 'text-white/60' : 'text-slate-600'}`}>
                      {data.totals[sys].toLocaleString()}
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Search */}
          <div className="relative">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" aria-hidden />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search sites…"
              aria-label="Search sites"
              className="form-input pl-8 pr-8 py-1.5 w-44 focus:w-56 transition-[width] duration-200"
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                aria-label="Clear search"
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors cursor-pointer"
              >
                <X size={13} />
              </button>
            )}
          </div>

          <button onClick={() => setShowInactive((v) => { localStorage.setItem('showInactive', String(!v)); return !v })} className="btn-ghost">
            {showInactive ? 'Hide Inactive' : 'Show Inactive'}
          </button>
          <Link to="/sites/add" className="btn-primary">
            <Plus size={13} aria-hidden /> Add Site
          </Link>
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto" style={{ WebkitOverflowScrolling: 'touch' }}>
          <table className="w-full" style={{ minWidth: '660px' }}>
            <thead>
              <tr className="border-b border-border bg-bg-elevated">
                <th className="w-8 px-4 py-3" />
                {([
                  { label: 'Site',       col: 'fullname'     as SortCol, cls: 'text-left' },
                  { label: 'System',     col: 'system_type'  as SortCol, cls: 'text-left' },
                  { label: 'Username',   col: null,                      cls: 'text-left' },
                  { label: 'Last Login', col: 'last_login'   as SortCol, cls: 'text-left' },
                  { label: 'Points',     col: 'queue_points' as SortCol, cls: 'text-left' },
                  { label: 'Active',     col: null,                      cls: 'text-left' },
                  { label: 'Actions',    col: null,                      cls: 'text-right' },
                ]).map(({ label, col, cls }) => (
                  <th
                    key={label}
                    onClick={col ? () => handleSort(col) : undefined}
                    className={`px-3 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500
                      ${cls} ${col ? 'cursor-pointer hover:text-slate-300 select-none' : ''}
                      ${label === 'Actions' ? 'pr-5' : ''}`}
                  >
                    {label}
                    {col && <SortBtn col={col} current={sortCol} asc={sortAsc} />}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-5 py-16 text-center">
                    <Inbox size={34} className="text-slate-700 mx-auto mb-3" aria-hidden />
                    {search.trim() ? (
                      <>
                        <p className="text-slate-400 font-medium text-sm">No results for "{search}"</p>
                        <p className="text-slate-600 text-xs mt-1">
                          Try a different search term or{' '}
                          <button onClick={() => setSearch('')} className="text-primary hover:text-primary-light underline cursor-pointer">
                            clear the search
                          </button>
                        </p>
                      </>
                    ) : (
                      <>
                        <p className="text-slate-400 font-medium text-sm">No sites to display</p>
                        <p className="text-slate-600 text-xs mt-1">
                          <Link to="/sites/add" className="text-primary hover:text-primary-light underline">
                            Add a site
                          </Link>{' '}
                          to get started
                        </p>
                      </>
                    )}
                  </td>
                </tr>
              ) : pageSlice.map((site) => (
                <SiteRow
                  key={site.url_name}
                  site={site}
                  expanded={expanded.has(site.url_name)}
                  onToggleExpand={() => toggleExpand(site.url_name)}
                  onToggleActive={() => handleToggle(site.url_name, site.active)}
                  onDeleteRequest={() => setConfirmDel(site.url_name)}
                  isDeleting={deletingId === site.url_name}
                />
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {filtered.length > PAGE_SIZE && (
        <div className="flex items-center justify-between px-1">
          <span className="text-xs text-slate-500">
            {pageStart}–{pageEnd} of {filtered.length}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={safePage === 0}
              className="btn-secondary px-3 py-1.5 text-xs disabled:opacity-30"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={safePage >= totalPages - 1}
              className="btn-secondary px-3 py-1.5 text-xs disabled:opacity-30"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {confirmDel && (
        <DeleteModal
          urlName={confirmDel}
          onConfirm={() => handleDelete(confirmDel)}
          onCancel={() => setConfirmDel(null)}
        />
      )}
    </div>
  )
}
