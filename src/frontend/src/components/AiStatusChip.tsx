import { useEffect, useState } from 'react'
import { getAiStatus } from '../api'
import type { AiStatus } from '../types'

// UI-UX §4.3a — a persistent, small status chip. "AI active" normally; while the
// LLM Router has exhausted both free tiers (TRD §3.1a) it shows the pause and
// when processing resumes. Polls every 30s so the chip self-corrects once the
// quota window rolls over, without a page reload.
export function AiStatusChip() {
  const [status, setStatus] = useState<AiStatus | null>(null)

  useEffect(() => {
    let alive = true
    const poll = () =>
      getAiStatus()
        .then((s) => alive && setStatus(s))
        .catch(() => alive && setStatus(null))
    poll()
    const id = setInterval(poll, 30_000)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [])

  if (status === null) {
    return <span className="text-xs text-stone-400">AI status unknown</span>
  }

  if (!status.paused) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
        AI active
      </span>
    )
  }

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">
      <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
      AI paused — free quota reached
      {status.resume_at && `, resuming ${new Date(status.resume_at).toLocaleString()}`}
    </span>
  )
}
