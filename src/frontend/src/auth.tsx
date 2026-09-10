import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { announceSession, setTokenGetter } from './api'
import { decideStatus } from './authStatus'
import type { AuthStatus } from './authStatus'
import { supabase } from './lib/supabase'

// Owner auth (06-Backend-Schema.md §5.1a). MFA is mandatory: a session only
// counts as `ready` at Authenticator Assurance Level 2 (password + TOTP code).
// The state machine itself lives in authStatus.ts (pure/testable).

export type { AuthStatus }

interface AuthValue {
  status: AuthStatus
  email: string | null
  error: string | null
  signIn: (email: string, password: string) => Promise<void>
  startEnroll: () => Promise<{ qrCode: string; secret: string }>
  submitCode: (code: string) => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthValue | null>(null)

async function resolveStatus(): Promise<AuthStatus> {
  const { data: { session } } = await supabase.auth.getSession()
  if (!session) return decideStatus({ hasSession: false, aalCurrent: null, hasVerifiedTotp: false })

  const { data: aal } = await supabase.auth.mfa.getAuthenticatorAssuranceLevel()
  const { data: factors } = await supabase.auth.mfa.listFactors()
  return decideStatus({
    hasSession: true,
    aalCurrent: aal?.currentLevel,
    hasVerifiedTotp: (factors?.totp ?? []).some((f) => f.status === 'verified'),
  })
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [email, setEmail] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  // Holds the factorId while an enroll or challenge is mid-flight.
  const pendingFactorId = useRef<string | null>(null)
  const announced = useRef(false)

  const refresh = useCallback(async () => {
    const next = await resolveStatus()
    setStatus(next)
    const { data: { user } } = await supabase.auth.getUser()
    setEmail(user?.email ?? null)
  }, [])

  useEffect(() => {
    setTokenGetter(async () => {
      const { data: { session } } = await supabase.auth.getSession()
      return session?.access_token ?? null
    })
    refresh()
    const { data: sub } = supabase.auth.onAuthStateChange(() => {
      refresh()
    })
    return () => sub.subscription.unsubscribe()
  }, [refresh])

  // Tell the backend once, on the transition into `ready`, so it can write the
  // owner_login audit row.
  useEffect(() => {
    if (status === 'ready' && !announced.current) {
      announced.current = true
      announceSession().catch(() => {
        announced.current = false // let it retry on next ready transition
      })
    }
    if (status !== 'ready') announced.current = false
  }, [status])

  const signIn = useCallback(async (e: string, password: string) => {
    setError(null)
    const { error: err } = await supabase.auth.signInWithPassword({ email: e, password })
    if (err) {
      setError(err.message)
      return
    }
    await refresh()
  }, [refresh])

  const startEnroll = useCallback(async () => {
    setError(null)
    // Clean up any half-finished unverified factor so a fresh enroll doesn't
    // collide. `.totp` holds only verified factors; unverified ones are in `.all`.
    const { data: factors } = await supabase.auth.mfa.listFactors()
    for (const f of factors?.all ?? []) {
      if (f.factor_type === 'totp' && f.status === 'unverified') {
        await supabase.auth.mfa.unenroll({ factorId: f.id })
      }
    }
    const { data, error: err } = await supabase.auth.mfa.enroll({
      factorType: 'totp',
      friendlyName: 'Owner authenticator',
    })
    if (err || !data) {
      setError(err?.message ?? 'Could not start MFA enrollment.')
      throw err ?? new Error('enroll failed')
    }
    pendingFactorId.current = data.id
    return { qrCode: data.totp.qr_code, secret: data.totp.secret }
  }, [])

  const submitCode = useCallback(async (code: string) => {
    setError(null)
    let factorId = pendingFactorId.current
    if (!factorId) {
      const { data: factors } = await supabase.auth.mfa.listFactors()
      factorId = (factors?.totp ?? []).find((f) => f.status === 'verified')?.id ?? null
    }
    if (!factorId) {
      setError('No authenticator to verify against.')
      return
    }
    const { data: challenge, error: cErr } = await supabase.auth.mfa.challenge({ factorId })
    if (cErr || !challenge) {
      setError(cErr?.message ?? 'Could not start the MFA challenge.')
      return
    }
    const { error: vErr } = await supabase.auth.mfa.verify({
      factorId,
      challengeId: challenge.id,
      code: code.trim(),
    })
    if (vErr) {
      setError(vErr.message)
      return
    }
    pendingFactorId.current = null
    await refresh()
  }, [refresh])

  const signOut = useCallback(async () => {
    await supabase.auth.signOut()
    pendingFactorId.current = null
    await refresh()
  }, [refresh])

  const value = useMemo<AuthValue>(
    () => ({ status, email, error, signIn, startEnroll, submitCode, signOut }),
    [status, email, error, signIn, startEnroll, submitCode, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>')
  return ctx
}
