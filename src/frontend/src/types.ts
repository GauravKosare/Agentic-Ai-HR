// Mirrors the backend Pydantic models so the two stay in lockstep. If a model
// changes in src/backend/app/agents/, change it here in the same commit.

export type WorkMode = 'onsite' | 'remote' | 'hybrid'

// app/agents/requirement_parser.py :: RequisitionDraft
export interface RequisitionDraft {
  role_title: string
  quantity: number
  work_mode: WorkMode | null
  duration: string | null
  compensation: string | null
  required_skills: string[]
  eligibility_rules: Record<string, unknown>
  clarifying_question: string | null
}

// app/agents/form_builder.py :: FieldType
export type FieldType =
  | 'text'
  | 'email'
  | 'tel'
  | 'file'
  | 'select'
  | 'radio'
  | 'textarea'
  | 'notice'

// app/agents/form_builder.py :: FormField
export interface FormField {
  field_id: string
  label: string
  field_type: FieldType
  required: boolean
  options: string[] | null
  help_text: string | null
}

// app/agents/form_builder.py :: FormSchema
export interface FormSchema {
  fields: FormField[]
}

// GET /system/ai-status
export interface AiStatus {
  paused: boolean
  resume_at: string | null
}

// app/core/auth.py :: Owner (returned by POST /auth/session)
export interface Owner {
  owner_id: string
  auth_user_id: string
  email: string
  full_name: string | null
}

// The shape the backend puts in an HTTPException detail for a 503 ai_paused or
// a 422 domain error (main.py :: _run_agent_call).
export interface ApiErrorDetail {
  error: 'ai_paused' | 'parsing_failed' | 'form_build_failed'
  resume_at?: string | null
  detail?: string
}
