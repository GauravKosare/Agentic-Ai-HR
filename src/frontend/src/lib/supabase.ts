import { createClient } from '@supabase/supabase-js'

// Uses the PUBLISHABLE key (sb_publishable_...), which is safe in the browser and
// subject to RLS. The secret key must never reach here. Values come from
// VITE_SUPABASE_* env vars — see .env.example.
const url = import.meta.env.VITE_SUPABASE_URL as string | undefined
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY as string | undefined

if (!url || !key) {
  // Surfaced loudly rather than failing with a confusing "fetch failed" later.
  console.error('VITE_SUPABASE_URL / VITE_SUPABASE_PUBLISHABLE_KEY are not set — auth will not work.')
}

export const supabase = createClient(url ?? '', key ?? '', {
  auth: { persistSession: true, autoRefreshToken: true },
})
