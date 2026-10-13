import { useAuth } from '@/features/auth/auth-context'

// Geçici ana sayfa. Dashboard (US-022) Sprint 6'da bu sayfanın yerini alacak.
export function HomePage() {
  const { user } = useAuth()

  return (
    <div className="grid gap-2">
      <h1 className="text-2xl font-semibold text-brand">Merhaba, {user?.full_name.split(' ')[0]} 👋</h1>
      <p className="text-muted-foreground">Projelerin ve görevlerin yakında burada olacak.</p>
    </div>
  )
}
