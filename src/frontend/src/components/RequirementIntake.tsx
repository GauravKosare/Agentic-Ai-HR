import { useState } from 'react'
import { ApiError, parseRequirement } from '../api'
import type { RequisitionDraft } from '../types'

// UI-UX §4.1 — "Tell me what you're hiring for", with example prompts. On a
// clear brief the AI returns a structured summary the Owner reviews; the
// conversation-first framing (not form-first) is a stated design principle.

const EXAMPLES = [
  '3 backend interns, remote, 3 months, ₹15k stipend, must know Python and SQL',
  '2 marketing interns, hybrid, 6 months, open to final-year students only',
  'One full-time frontend engineer, onsite Nagpur, React + TypeScript, 8-12 LPA',
]

interface Props {
  onParsed: (requisition: RequisitionDraft) => void
}

export function RequirementIntake({ onParsed }: Props) {
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [paused, setPaused] = useState<{ resumeAt: string | null } | null>(null)

  async function submit() {
    if (!text.trim() || busy) return
    setBusy(true)
    setError(null)
    setPaused(null)
    try {
      onParsed(await parseRequirement(text.trim()))
    } catch (e) {
      if (e instanceof ApiError && e.paused) {
        setPaused({ resumeAt: e.resumeAt })
      } else {
        setError(e instanceof Error ? e.message : 'Something went wrong.')
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-stone-800">Tell me what you're hiring for</h2>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit()
        }}
        rows={4}
        placeholder="e.g. 3 backend interns, remote, 3 months, ₹15k stipend, must know Python and SQL"
        className="w-full rounded-xl border border-stone-200 bg-white px-4 py-3 text-sm text-stone-800 shadow-sm focus:border-stone-400 focus:outline-none"
      />

      <div className="flex flex-wrap gap-2">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => setText(ex)}
            className="rounded-full border border-stone-200 bg-white px-3 py-1 text-xs text-stone-500 hover:border-stone-300 hover:text-stone-700"
          >
            {ex}
          </button>
        ))}
      </div>

      {paused && (
        <div className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
          The AI is paused — today's free request quota is used up.
          {paused.resumeAt && ` Processing resumes automatically around ${new Date(paused.resumeAt).toLocaleString()}.`}
        </div>
      )}
      {error && <div className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>}

      <button
        onClick={submit}
        disabled={busy || !text.trim()}
        className="rounded-lg bg-stone-800 px-4 py-2 text-sm font-medium text-white hover:bg-stone-900 disabled:opacity-50"
      >
        {busy ? 'Reading your brief…' : 'Continue'}
      </button>
      <p className="text-xs text-stone-400">Tip: ⌘/Ctrl + Enter to submit</p>
    </div>
  )
}
