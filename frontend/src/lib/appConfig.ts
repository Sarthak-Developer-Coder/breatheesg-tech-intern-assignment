import type { ApiConfig } from './api'

const STORAGE_KEY = 'tech-intern-assignment-config-v1'

export function defaultConfig(): ApiConfig {
  const baseUrl =
    (import.meta.env.VITE_API_BASE_URL as string | undefined) ||
    'http://127.0.0.1:8000'

  return {
    baseUrl,
    tenantSlug: 'demo',
    actor: 'analyst@demo.local',
  }
}

export function loadConfig(): ApiConfig {
  const fallback = defaultConfig()
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return fallback
    const parsed = JSON.parse(raw) as Partial<ApiConfig>
    return {
      baseUrl: typeof parsed.baseUrl === 'string' ? parsed.baseUrl : fallback.baseUrl,
      tenantSlug:
        typeof parsed.tenantSlug === 'string' ? parsed.tenantSlug : fallback.tenantSlug,
      actor: typeof parsed.actor === 'string' ? parsed.actor : fallback.actor,
    }
  } catch {
    return fallback
  }
}

export function saveConfig(cfg: ApiConfig): void {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      baseUrl: cfg.baseUrl,
      tenantSlug: cfg.tenantSlug,
      actor: cfg.actor,
    }),
  )
}
