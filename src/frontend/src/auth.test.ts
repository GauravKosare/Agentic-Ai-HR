import { describe, expect, it } from 'vitest'
import { decideStatus } from './authStatus'

describe('decideStatus', () => {
  it('no session -> signed_out', () => {
    expect(decideStatus({ hasSession: false, aalCurrent: null, hasVerifiedTotp: false })).toBe('signed_out')
  })

  it('session at aal2 -> ready (MFA satisfied)', () => {
    expect(decideStatus({ hasSession: true, aalCurrent: 'aal2', hasVerifiedTotp: true })).toBe('ready')
  })

  it('session at aal1, no verified factor -> needs_mfa_enroll', () => {
    expect(decideStatus({ hasSession: true, aalCurrent: 'aal1', hasVerifiedTotp: false })).toBe(
      'needs_mfa_enroll',
    )
  })

  it('session at aal1, a verified factor exists -> needs_mfa_code', () => {
    expect(decideStatus({ hasSession: true, aalCurrent: 'aal1', hasVerifiedTotp: true })).toBe(
      'needs_mfa_code',
    )
  })

  it('aal1 is never treated as ready even with a verified factor', () => {
    // The whole point: a password-only session must not unlock the console.
    expect(decideStatus({ hasSession: true, aalCurrent: 'aal1', hasVerifiedTotp: true })).not.toBe('ready')
  })
})
