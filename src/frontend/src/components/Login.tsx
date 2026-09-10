import { useEffect, useState } from 'react'
import { useAuth } from '../auth'

// Renders whichever pre-`ready` auth step the session is at (06-Backend-Schema.md
// §5.1a). MFA is not optional — you can't reach the console at aal1.

const box = 'w-full max-w-sm space-y-4 rounded-xl border border-stone-200 bg-white p-6 shadow-sm'
const input =
  'w-full rounded-md border border-stone-200 px-3 py-2 text-sm focus:border-stone-400 focus:outline-none'
const button =
  'w-full rounded-lg bg-stone-800 px-4 py-2 text-sm font-medium text-white hover:bg-stone-900 disabled:opacity-50'

export function Login() {
  const { status, error, signIn, startEnroll, submitCode } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [enroll, setEnroll] = useState<{ qrCode: string; secret: string } | null>(null)

  // When we land on the enroll step, kick off enrollment to get the QR.
  useEffect(() => {
    if (status === 'needs_mfa_enroll' && !enroll) {
      startEnroll()
        .then(setEnroll)
        .catch(() => {})
    }
    if (status !== 'needs_mfa_enroll') setEnroll(null)
  }, [status, enroll, startEnroll])

  const wrap = (fn: () => Promise<void>) => async () => {
    setBusy(true)
    try {
      await fn()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-stone-50 px-4">
      {status === 'signed_out' && (
        <div className={box}>
          <h1 className="text-lg font-semibold text-stone-800">Sign in</h1>
          <input
            className={input}
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            className={input}
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && wrap(() => signIn(email, password))()}
          />
          {error && <p className="text-sm text-rose-600">{error}</p>}
          <button className={button} disabled={busy || !email || !password} onClick={wrap(() => signIn(email, password))}>
            {busy ? 'Signing in…' : 'Continue'}
          </button>
        </div>
      )}

      {status === 'needs_mfa_enroll' && (
        <div className={box}>
          <h1 className="text-lg font-semibold text-stone-800">Set up two-factor authentication</h1>
          <p className="text-sm text-stone-500">
            Required. Scan this with an authenticator app (Google Authenticator, Authy, 1Password), then enter
            the 6-digit code.
          </p>
          {enroll ? (
            <>
              <img
                src={enroll.qrCode}
                alt="Authenticator QR code"
                className="mx-auto h-44 w-44 rounded-md border border-stone-200"
              />
              <p className="break-all text-center text-xs text-stone-400">
                Can't scan? Enter this key manually: <span className="font-mono">{enroll.secret}</span>
              </p>
            </>
          ) : (
            <p className="text-sm text-stone-400">Loading QR code…</p>
          )}
          <input
            className={`${input} text-center tracking-widest`}
            inputMode="numeric"
            maxLength={6}
            placeholder="000000"
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
            onKeyDown={(e) => e.key === 'Enter' && code.length === 6 && wrap(() => submitCode(code))()}
          />
          {error && <p className="text-sm text-rose-600">{error}</p>}
          <button className={button} disabled={busy || code.length !== 6} onClick={wrap(() => submitCode(code))}>
            {busy ? 'Verifying…' : 'Verify and continue'}
          </button>
        </div>
      )}

      {status === 'needs_mfa_code' && (
        <div className={box}>
          <h1 className="text-lg font-semibold text-stone-800">Enter your 6-digit code</h1>
          <p className="text-sm text-stone-500">From your authenticator app.</p>
          <input
            className={`${input} text-center tracking-widest`}
            inputMode="numeric"
            maxLength={6}
            placeholder="000000"
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
            onKeyDown={(e) => e.key === 'Enter' && code.length === 6 && wrap(() => submitCode(code))()}
            autoFocus
          />
          {error && <p className="text-sm text-rose-600">{error}</p>}
          <button className={button} disabled={busy || code.length !== 6} onClick={wrap(() => submitCode(code))}>
            {busy ? 'Verifying…' : 'Verify'}
          </button>
        </div>
      )}
    </div>
  )
}
