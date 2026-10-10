import { Navigate, Outlet, useLocation } from 'react-router'
import { Loader2Icon } from 'lucide-react'
import { useAuth } from './auth-context'

function FullScreenLoader() {
  return (
    <div className="flex min-h-svh items-center justify-center">
      <Loader2Icon className="size-6 animate-spin text-primary" />
    </div>
  )
}

// Giriş gerektiren sayfalar. Oturum yoksa giriş sayfasına, geldiği adresi hatırlayarak gönderir.
export function ProtectedRoute() {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') return <FullScreenLoader />
  if (status === 'unauthenticated') {
    return <Navigate to="/giris" replace state={{ from: location.pathname }} />
  }
  return <Outlet />
}

// Sadece sistem rolü Yönetici olanların girebildiği sayfalar (FR-012)
export function AdminRoute() {
  const { isAdmin } = useAuth()
  if (!isAdmin) return <Navigate to="/" replace />
  return <Outlet />
}

// Giriş yapmış kullanıcı giriş/kayıt sayfasını görmesin. Girişten sonra geldiği sayfaya döner.
export function GuestRoute() {
  const { status } = useAuth()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/'

  if (status === 'loading') return <FullScreenLoader />
  if (status === 'authenticated') return <Navigate to={from} replace />
  return <Outlet />
}
