/**
 * Auth state machine — pure, no imports. Kept separate from auth.tsx (which
 * pulls in the Supabase client) so the decision logic is testable on its own.
 *
 *   loading            — checking for an existing session
 *   signed_out         — no session; show email/password
 *   needs_mfa_enroll   — session at aal1, no verified TOTP factor; show QR to scan
 *   needs_mfa_code      — session at aal1, a verified factor exists; show code entry
 *   ready              — session at aal2; the console is unlocked
 */
export type AuthStatus = 'loading' | 'signed_out' | 'needs_mfa_enroll' | 'needs_mfa_code' | 'ready'

/**
 * `ready` requires aal2 (MFA passed). An aal1 session goes to enrollment if
 * there's no verified TOTP factor yet, otherwise to the code prompt — a
 * password-only session never unlocks the console.
 */
export function decideStatus(input: {
  hasSession: boolean
  aalCurrent: string | null | undefined
  hasVerifiedTotp: boolean
}): AuthStatus {
  if (!input.hasSession) return 'signed_out'
  if (input.aalCurrent === 'aal2') return 'ready'
  return input.hasVerifiedTotp ? 'needs_mfa_code' : 'needs_mfa_enroll'
}
