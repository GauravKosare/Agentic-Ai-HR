import type { AiStatus, ApiErrorDetail, FormSchema, Owner, RequisitionDraft } from './types'

// Dev: '/api' is proxied to the backend by Vite (vite.config.ts).
// Prod: set VITE_API_BASE_URL to the deployed backend's origin.
const BASE = import.meta.env.VITE_API_BASE_URL ?? '/api'

// The AuthProvider registers a getter here so `request` can attach the current
// Supabase access token without api.ts importing anything React/Supabase.
let tokenGetter: (() => Promise<string | null>) | null = null
export function setTokenGetter(fn: () => Promise<string | null>) {
  tokenGetter = fn
}

/**
 * Thrown for any non-2xx response. `paused` is true when the backend returned a
 * 503 `ai_paused` (UI-UX §4.3a). `unauthorized` is true on 401/403 so the app
 * can bounce back to login rather than showing a generic error.
 */
export class ApiError extends Error {
  readonly status: number
  readonly paused: boolean
  readonly unauthorized: boolean
  readonly resumeAt: string | null

  constructor(status: number, detail: ApiErrorDetail | string | undefined) {
    const d = typeof detail === 'object' ? detail : undefined
    super(d?.detail || (typeof detail === 'string' ? detail : `Request failed (${status})`))
    this.status = status
    this.paused = d?.error === 'ai_paused'
    this.unauthorized = status === 401 || status === 403
    this.resumeAt = d?.resume_at ?? null
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = tokenGetter ? await tokenGetter() : null
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  })
  if (!res.ok) {
    let detail: ApiErrorDetail | string | undefined
    try {
      detail = (await res.json())?.detail
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

// Unauthenticated — the AI status chip polls this before login too.
export function getAiStatus(): Promise<AiStatus> {
  return request<AiStatus>('/system/ai-status')
}

// Called once by the AuthProvider when a session reaches aal2 — lets the backend
// write the owner_login audit row.
export function announceSession(): Promise<Owner> {
  return request<Owner>('/auth/session', { method: 'POST' })
}

export function parseRequirement(rawBriefText: string): Promise<RequisitionDraft> {
  return request<RequisitionDraft>('/requisitions/parse', {
    method: 'POST',
    body: JSON.stringify({ raw_brief_text: rawBriefText }),
  })
}

export function buildForm(requisition: RequisitionDraft): Promise<FormSchema> {
  return request<FormSchema>('/forms/build', {
    method: 'POST',
    body: JSON.stringify(requisition),
  })
}
