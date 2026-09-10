import type { FormSchema } from '../types'

// UI-UX §4.2 — "Live preview of the candidate-facing form exactly as it will
// appear." Read-only here: this pass renders the form the Form Builder Agent
// produced; per-field inline editing (add/remove/reword) is a later refinement.
// The primary edit path for now is changing the requisition above and
// regenerating, since the requisition is the source of truth (TRD Stage 1).

export function FormPreview({ form }: { form: FormSchema }) {
  return (
    <div className="mx-auto max-w-md space-y-5 rounded-xl border border-stone-200 bg-white p-6 shadow-sm">
      <p className="text-center text-xs uppercase tracking-wide text-stone-400">
        Candidate-facing form preview
      </p>

      {form.fields.map((field) => {
        if (field.field_type === 'notice') {
          return (
            <p key={field.field_id} className="rounded-lg bg-stone-50 px-3 py-2 text-sm leading-relaxed text-stone-600">
              {field.label}
            </p>
          )
        }

        return (
          <div key={field.field_id} className="space-y-1.5">
            <label className="block text-sm font-medium text-stone-700">
              {field.label}
              {field.required && <span className="ml-0.5 text-rose-500">*</span>}
            </label>

            {field.field_type === 'textarea' ? (
              <textarea
                disabled
                rows={3}
                className="w-full rounded-md border border-stone-200 bg-stone-50 px-3 py-2 text-sm"
              />
            ) : field.field_type === 'select' ? (
              <select disabled className="w-full rounded-md border border-stone-200 bg-stone-50 px-3 py-2 text-sm">
                {(field.options ?? []).map((o) => (
                  <option key={o}>{o}</option>
                ))}
              </select>
            ) : field.field_type === 'radio' ? (
              <div className="space-y-1">
                {(field.options ?? []).map((o) => (
                  <label key={o} className="flex items-center gap-2 text-sm text-stone-600">
                    <input type="radio" disabled name={field.field_id} />
                    {o}
                  </label>
                ))}
              </div>
            ) : field.field_type === 'file' ? (
              <div className="rounded-md border border-dashed border-stone-300 bg-stone-50 px-3 py-3 text-center text-sm text-stone-400">
                Upload {field.label.toLowerCase()}
              </div>
            ) : (
              <input
                disabled
                type={field.field_type}
                className="w-full rounded-md border border-stone-200 bg-stone-50 px-3 py-2 text-sm"
              />
            )}

            {field.help_text && <p className="text-xs text-stone-400">{field.help_text}</p>}
          </div>
        )
      })}

      <button
        disabled
        className="w-full rounded-lg bg-stone-800 px-4 py-2 text-sm font-medium text-white opacity-60"
      >
        Submit application
      </button>
    </div>
  )
}
