import { Navigate, Route, Routes } from 'react-router'
import { AppLayout } from '@/components/layout/AppLayout'
import { AuthPage } from '@/features/auth/AuthPage'
import { AdminRoute, GuestRoute, ProtectedRoute } from '@/features/auth/RouteGuards'
import { UsersPage } from '@/features/users/UsersPage'
import { HomePage } from '@/pages/HomePage'

export default function App() {
  return (
    <Routes>
      <Route element={<GuestRoute />}>
        <Route path="/giris" element={<AuthPage />} />
        <Route path="/kayit" element={<AuthPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<HomePage />} />
          <Route element={<AdminRoute />}>
            <Route path="/kullanicilar" element={<UsersPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
