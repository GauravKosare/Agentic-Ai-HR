import { AuthProvider, useAuth } from './auth'
import { Console } from './Console'
import { Login } from './components/Login'

function Gate() {
  const { status } = useAuth()

  if (status === 'loading') {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-stone-400">Loading…</div>
    )
  }
  if (status === 'ready') return <Console />
  return <Login />
}

export default function App() {
  return (
    <AuthProvider>
      <Gate />
    </AuthProvider>
  )
}
