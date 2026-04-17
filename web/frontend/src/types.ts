export interface QueueDetail {
  name: string
  points: number
  unit: string
}

export interface Site {
  url_name: string
  fullname: string
  system_type: string
  momentum_id?: string | null
  base_url?: string | null
  username?: string | null
  active: boolean
  last_login?: string | null
  queue_points?: number | null
  queue_details: QueueDetail[]
}

export interface SiteFormData {
  url_name: string
  fullname: string
  system_type: string
  momentum_id: string
  base_url: string
  username: string
  password: string
  active: boolean
}

export interface SitesResponse {
  sites: Site[]
  totals: Record<string, number>
  api_key_missing: boolean
}

export interface ContainerStatus {
  container_status: string
  finished_at?: string | null
  last_logins: Record<string, string | null>
}

export interface Toast {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
}
