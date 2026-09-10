import type { AiStatus, ApiErrorDetail, FormSchema, RequisitionDraft } from './types'

// Dev: '/api' is proxied to the backend by Vite (vite.config.ts).
// Prod: set VITE_API_BASE_URL to the deployed backend's origin.
const BASE = import.meta.env.VITE_API_BASE_URL ?? '/api'

/**
 * Thrown for any non-2xx response. `paused` is set true when the backend
 * returned a 503 with error 'ai_paused' — the Owner Console treats that
 * distinctly from a real failure (UI-UX §4.3a), so callers check it rather
 * than showing a generic error.
 */
export class ApiError extends Error {
  readonly status: number
  readonly paused: boolean
  readonly resumeAt: string | null

  constructor(status: number, detail: ApiErrorDetail | string | undefined) {
    const d = typeof detail === 'object' ? detail : undefined
    super(d?.detail || (typeof detail === 'string' ? detail : `Request failed (${status})`))
    this.status = status
    this.paused = d?.error === 'ai_paused'
    this.resumeAt = d?.resume_at ?? null
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!res.ok) {
    let detail: ApiErrorDetail | string | undefined
    try {
      const body = await res.json()
      detail = body?.detail
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

export function getAiStatus(): Promise<AiStatus> {
  return request<AiStatus>('/system/ai-status')
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
