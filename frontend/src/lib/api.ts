export type ApiConfig = {
  baseUrl: string
  tenantSlug: string
  actor: string
}

export type Paginated<T> = {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export type IngestionJob = {
  id: number
  tenant_id: number
  source_type: string
  status: string
  created_by: string
  source_label: string
  original_filename: string
  raw_record_count: number
  parsed_record_count: number
  failed_record_count: number
  activity_record_count: number
  anomaly_record_count: number
  started_at: string | null
  finished_at: string | null
  error_message: string
  summary: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export type ActivityRecordListItem = {
  id: number
  tenant_id: number
  ingestion_job_id: number | null
  raw_record_id: number | null
  source_type: string
  source_external_id: string
  scope: string
  category: string
  subcategory: string
  plant_id: number | null
  plant_code: string
  plant_name: string
  activity_date: string | null
  period_start: string | null
  period_end: string | null
  source_quantity: string
  source_unit: string
  quantity: string
  normalized_unit: string
  co2e_kg: string
  anomaly_flags: string[]
  confidence_score: number
  review_status: string
  approved_at: string | null
  approved_by: string
  locked_at: string | null
  locked_by: string
  last_edited_at: string | null
  last_edited_by: string
  created_at: string
  updated_at: string
}

export type ActivityRecordDetail = ActivityRecordListItem & {
  emission_factor_id: number | null
  emission_factor_snapshot: Record<string, unknown> | null
  activity_metadata: Record<string, unknown>
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/+$/, '')
}

function buildQuery(params?: Record<string, unknown>): string {
  if (!params) return ''
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    search.set(key, String(value))
  }
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

async function apiFetch<T>(
  config: ApiConfig,
  path: string,
  init?: RequestInit,
): Promise<T> {
  const url = path.startsWith('http')
    ? path
    : `${normalizeBaseUrl(config.baseUrl)}${path}`

  const headers = new Headers(init?.headers)
  headers.set('X-Tenant-Slug', config.tenantSlug)
  if (config.actor) headers.set('X-Actor', config.actor)

  const res = await fetch(url, {
    ...init,
    headers,
  })

  if (!res.ok) {
    let detail = ''
    try {
      const data = (await res.json()) as { detail?: string }
      detail = data?.detail ? `: ${data.detail}` : ''
    } catch {
      try {
        const text = await res.text()
        detail = text ? `: ${text}` : ''
      } catch {
        // ignore
      }
    }

    throw new Error(`HTTP ${res.status} ${res.statusText}${detail}`)
  }

  return (await res.json()) as T
}

export async function uploadSapCsv(
  config: ApiConfig,
  file: File,
  sourceLabel: string,
): Promise<IngestionJob> {
  const form = new FormData()
  form.append('file', file)
  form.append('actor', config.actor)
  if (sourceLabel) form.append('source_label', sourceLabel)

  return apiFetch<IngestionJob>(config, '/api/upload/sap', {
    method: 'POST',
    body: form,
  })
}

export async function uploadUtilityCsv(
  config: ApiConfig,
  file: File,
  sourceLabel: string,
): Promise<IngestionJob> {
  const form = new FormData()
  form.append('file', file)
  form.append('actor', config.actor)
  if (sourceLabel) form.append('source_label', sourceLabel)

  return apiFetch<IngestionJob>(config, '/api/upload/utility', {
    method: 'POST',
    body: form,
  })
}

export async function uploadTravelPayload(
  config: ApiConfig,
  payload: Record<string, unknown>,
  sourceLabel: string,
): Promise<IngestionJob> {
  const body = JSON.stringify({
    actor: config.actor,
    source_label: sourceLabel,
    ...payload,
  })

  return apiFetch<IngestionJob>(config, '/api/upload/travel', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body,
  })
}

export async function listIngestionJobs(
  config: ApiConfig,
  params?: Record<string, unknown>,
): Promise<Paginated<IngestionJob>> {
  return apiFetch<Paginated<IngestionJob>>(
    config,
    `/api/ingestion-jobs${buildQuery(params)}`,
  )
}

export async function listActivityRecords(
  config: ApiConfig,
  params?: Record<string, unknown>,
): Promise<Paginated<ActivityRecordListItem>> {
  return apiFetch<Paginated<ActivityRecordListItem>>(
    config,
    `/api/activity-records${buildQuery(params)}`,
  )
}

export async function listReviewQueue(
  config: ApiConfig,
  params?: Record<string, unknown>,
): Promise<Paginated<ActivityRecordListItem>> {
  return apiFetch<Paginated<ActivityRecordListItem>>(
    config,
    `/api/review-queue${buildQuery(params)}`,
  )
}

export async function getActivityRecord(
  config: ApiConfig,
  id: number,
): Promise<ActivityRecordDetail> {
  return apiFetch<ActivityRecordDetail>(config, `/api/activity-records/${id}`)
}

export async function editActivityRecord(
  config: ApiConfig,
  id: number,
  updates: Partial<
    Pick<
      ActivityRecordDetail,
      | 'scope'
      | 'category'
      | 'subcategory'
      | 'plant_id'
      | 'activity_date'
      | 'period_start'
      | 'period_end'
      | 'quantity'
      | 'normalized_unit'
      | 'activity_metadata'
    >
  >,
  reason: string,
): Promise<ActivityRecordDetail> {
  const body = JSON.stringify({
    actor: config.actor,
    reason,
    ...updates,
  })

  return apiFetch<ActivityRecordDetail>(config, `/api/activity-records/${id}/edit`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body,
  })
}

export async function approveActivityRecord(
  config: ApiConfig,
  id: number,
  reason: string,
): Promise<ActivityRecordDetail> {
  const body = JSON.stringify({
    actor: config.actor,
    reason,
  })

  return apiFetch<ActivityRecordDetail>(config, `/api/review/${id}/approve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body,
  })
}

export async function rejectActivityRecord(
  config: ApiConfig,
  id: number,
  reason: string,
): Promise<ActivityRecordDetail> {
  const body = JSON.stringify({
    actor: config.actor,
    reason,
  })

  return apiFetch<ActivityRecordDetail>(config, `/api/review/${id}/reject`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body,
  })
}
