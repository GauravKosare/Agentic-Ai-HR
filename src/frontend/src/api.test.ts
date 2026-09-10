import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, getAiStatus, parseRequirement, setTokenGetter } from './api'

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  })
}

afterEach(() => {
  vi.restoreAllMocks()
  setTokenGetter(async () => null)
})

describe('api client', () => {
  it('attaches the bearer token when the getter returns one', async () => {
    const fetchMock = mockFetch(200, { paused: false, resume_at: null })
    vi.stubGlobal('fetch', fetchMock)
    setTokenGetter(async () => 'test-token')

    await getAiStatus()

    const [, init] = fetchMock.mock.calls[0]
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer test-token')
  })

  it('omits the Authorization header when there is no token', async () => {
    const fetchMock = mockFetch(200, { paused: false, resume_at: null })
    vi.stubGlobal('fetch', fetchMock)
    setTokenGetter(async () => null)

    await getAiStatus()

    const [, init] = fetchMock.mock.calls[0]
    expect('Authorization' in (init.headers as Record<string, string>)).toBe(false)
  })

  it('flags 401/403 as unauthorized so the app can bounce to login', async () => {
    vi.stubGlobal('fetch', mockFetch(401, { detail: { error: 'auth_failed', detail: 'token expired' } }))
    await expect(parseRequirement('x')).rejects.toMatchObject({ unauthorized: true })
  })

  it('flags a 503 ai_paused response distinctly from a real error', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch(503, { detail: { error: 'ai_paused', resume_at: '2026-01-01T00:00:00+00:00' } }),
    )
    try {
      await parseRequirement('x')
      throw new Error('should have thrown')
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError)
      expect((e as ApiError).paused).toBe(true)
      expect((e as ApiError).unauthorized).toBe(false)
    }
  })
})
