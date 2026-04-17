import type { SiteFormData, SitesResponse, ContainerStatus } from './types'

async function req<T>(url: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`)
  return data as T
}

export const api = {
  sites: {
    list: () => req<SitesResponse>('/api/sites'),
    get:  (id: string) => req<SiteFormData & { queue_details?: unknown[] }>(`/api/sites/${id}`),
    create: (data: SiteFormData) =>
      req<{ ok: boolean }>('/api/sites', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: SiteFormData) =>
      req<{ ok: boolean }>(`/api/sites/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (id: string) =>
      req<{ ok: boolean }>(`/api/sites/${id}`, { method: 'DELETE' }),
    toggleActive: (id: string) =>
      req<{ active: boolean }>(`/api/sites/${id}/toggle-active`, { method: 'POST' }),
  },
  status: () => req<ContainerStatus>('/api/status'),
  run:    () => req<{ ok: boolean; message: string }>('/api/run', { method: 'POST' }),
  settings: {
    get:    () => req<{ momentum_api_key: string; api_key_missing: boolean }>('/api/settings'),
    update: (d: { momentum_api_key: string }) =>
      req<{ ok: boolean }>('/api/settings', { method: 'POST', body: JSON.stringify(d) }),
  },
}
