import { useState } from 'react'
import { ApiError, buildForm } from './api'
import { AiStatusChip } from './components/AiStatusChip'
import { FormPreview } from './components/FormPreview'
import { RequirementIntake } from './components/RequirementIntake'
import { RequisitionCard } from './components/RequisitionCard'
import type { FormSchema, RequisitionDraft } from './types'

type Step = 'intake' | 'review'

export default function App() {
  const [step, setStep] = useState<Step>('intake')
  const [requisition, setRequisition] = useState<RequisitionDraft | null>(null)
  const [form, setForm] = useState<FormSchema | null>(null)
  const [formStale, setFormStale] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [approved, setApproved] = useState(false)

  async function generateForm(req: RequisitionDraft) {
    setBusy(true)
    setError(null)
    try {
      setForm(await buildForm(req))
      setFormStale(false)
    } catch (e) {
      if (e instanceof ApiError && e.paused) {
        setError(
          'The AI is paused — today\'s free request quota is used up. The form will generate once it resumes.',
        )
      } else {
        setError(e instanceof Error ? e.message : 'Could not generate the form.')
      }
    } finally {
      setBusy(false)
    }
  }

  async function onParsed(req: RequisitionDraft) {
    setRequisition(req)
    setApproved(false)
    setStep('review')
    await generateForm(req)
  }

  function onRequisitionChange(next: RequisitionDraft) {
    setRequisition(next)
    setFormStale(true)
    setApproved(false)
  }

  function startOver() {
    setStep('intake')
    setRequisition(null)
    setForm(null)
    setFormStale(false)
    setError(null)
    setApproved(false)
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-3">
          <span className="text-sm font-semibold text-stone-800">AI Recruiter Agent</span>
          <AiStatusChip />
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-10">
        {step === 'intake' && <RequirementIntake onParsed={onParsed} />}

        {step === 'review' && requisition && (
          <div className="space-y-8">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-stone-800">Review the requisition</h2>
              <button onClick={startOver} className="text-sm text-stone-500 hover:text-stone-700">
                Start over
              </button>
            </div>

            <RequisitionCard requisition={requisition} onChange={onRequisitionChange} />

            {error && <div className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>}

            {formStale && (
              <div className="flex items-center justify-between rounded-lg bg-stone-100 px-4 py-2 text-sm text-stone-600">
                <span>The requisition changed — regenerate the form to match.</span>
                <button
                  onClick={() => generateForm(requisition)}
                  disabled={busy}
                  className="rounded-md bg-stone-800 px-3 py-1 text-xs font-medium text-white disabled:opacity-50"
                >
                  {busy ? 'Regenerating…' : 'Regenerate form'}
                </button>
              </div>
            )}

            {busy && !form && <p className="text-sm text-stone-500">Generating the application form…</p>}

            {form && (
              <>
                <FormPreview form={form} />

                {approved ? (
                  <div className="rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                    <span className="font-medium">Form approved.</span> Next step — distributing it to job
                    platforms — isn't built yet (Implementation Plan Phase 2), so nothing is posted publicly.
                  </div>
                ) : (
                  <div className="flex justify-end">
                    <button
                      onClick={() => setApproved(true)}
                      disabled={formStale || busy}
                      className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                      title={formStale ? 'Regenerate the form first' : undefined}
                    >
                      Approve form
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
