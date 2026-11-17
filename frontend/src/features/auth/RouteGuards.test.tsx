// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { AdminRoute } from './RouteGuards'
import * as authContext from './auth-context'

afterEach(() => { cleanup(); vi.restoreAllMocks() })

function mockAuth(isAdmin: boolean) {
  vi.spyOn(authContext, 'useAuth').mockReturnValue({
    user: null,
    status: 'authenticated',
    isAdmin,
    signIn: () => {},
    signOut: async () => {},
  })
}

function mountAdminPage() {
  return render(
    <MemoryRouter initialEntries={['/kullanicilar']}>
      <Routes>
        <Route element={<AdminRoute />}>
          <Route path="/kullanicilar" element={<p>Kullanıcı listesi</p>} />
        </Route>
        <Route path="/" element={<p>Kontrol paneli</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('AdminRoute (#145, FR-012)', () => {
  it('Ekip Üyesi yönetici sayfasını açınca yetkisiz işlem mesajı görür, veri görmez', () => {
    mockAuth(false)
    mountAdminPage()
    expect(screen.getByText('Bu işlem için yetkiniz yok')).toBeTruthy()
    expect(screen.queryByText('Kullanıcı listesi')).toBeNull()
    expect(screen.queryByText('Kontrol paneli')).toBeNull()
  })

  it('Yönetici sayfayı normal görür', () => {
    mockAuth(true)
    mountAdminPage()
    expect(screen.getByText('Kullanıcı listesi')).toBeTruthy()
    expect(screen.queryByText('Bu işlem için yetkiniz yok')).toBeNull()
  })
})
