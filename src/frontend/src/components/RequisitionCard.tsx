import type { ReactNode } from 'react'
import type { RequisitionDraft, WorkMode } from '../types'

// UI-UX §4.1 / §4.2 — the structured summary card. Editable inline: the
// requisition is "the single source of truth for the form, screening rubric,
// and interview question bank" (TRD Stage 1), so this is where the Owner
// corrects the AI's read before anything is generated from it.

const WORK_MODES: WorkMode[] = ['onsite', 'remote', 'hybrid']

interface Props {
  requisition: RequisitionDraft
  onChange: (next: RequisitionDraft) => void
}

function Label({ children }: { children: ReactNode }) {
  return <span className="text-xs font-medium uppercase tracking-wide text-stone-400">{children}</span>
}

const inputClass =
  'w-full rounded-md border border-stone-200 bg-white px-3 py-1.5 text-sm text-stone-800 focus:border-stone-400 focus:outline-none'

export function RequisitionCard({ requisition: r, onChange }: Props) {
  const set = <K extends keyof RequisitionDraft>(key: K, value: RequisitionDraft[K]) =>
    onChange({ ...r, [key]: value })

  return (
    <div className="space-y-4 rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      {r.clarifying_question && (
        <div className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
          <span className="font-medium">One thing to check: </span>
          {r.clarifying_question}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="space-y-1">
          <Label>Role title</Label>
          <input className={inputClass} value={r.role_title} onChange={(e) => set('role_title', e.target.value)} />
        </label>

        <label className="space-y-1">
          <Label>Openings</Label>
          <input
            type="number"
            min={1}
            className={inputClass}
            value={r.quantity}
            onChange={(e) => set('quantity', Math.max(1, Number(e.target.value) || 1))}
          />
        </label>

        <label className="space-y-1">
          <Label>Work mode</Label>
          <select
            className={inputClass}
            value={r.work_mode ?? ''}
            onChange={(e) => set('work_mode', (e.target.value || null) as WorkMode | null)}
          >
            <option value="">— not specified —</option>
            {WORK_MODES.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-1">
          <Label>Duration</Label>
          <input
            className={inputClass}
            value={r.duration ?? ''}
            placeholder="e.g. 3 months, permanent"
            onChange={(e) => set('duration', e.target.value || null)}
          />
        </label>

        <label className="space-y-1">
          <Label>Compensation</Label>
          <input
            className={inputClass}
            value={r.compensation ?? ''}
            placeholder="e.g. ₹15,000/month"
            onChange={(e) => set('compensation', e.target.value || null)}
          />
        </label>

        <label className="space-y-1 sm:col-span-2">
          <Label>Required skills (comma-separated)</Label>
          <input
            className={inputClass}
            value={r.required_skills.join(', ')}
            onChange={(e) =>
              set(
                'required_skills',
                e.target.value
                  .split(',')
                  .map((s) => s.trim())
                  .filter(Boolean),
              )
            }
          />
        </label>
      </div>

      {Object.keys(r.eligibility_rules).length > 0 && (
        <div className="space-y-1">
          <Label>Eligibility</Label>
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(r.eligibility_rules).map(([k, v]) => (
              <span key={k} className="rounded-md bg-stone-100 px-2 py-1 text-xs text-stone-600">
                {k}: {String(v)}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
