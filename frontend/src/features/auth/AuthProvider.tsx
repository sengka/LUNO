import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { setUnauthorizedHandler } from '@/lib/api'
import { clearToken, getToken, setToken } from '@/lib/token'
import type { LoginResponse } from '@/types/api'
import { authApi } from './api'
import { AuthContext, type AuthContextValue, type AuthStatus } from './auth-context'

const ME_QUERY_KEY = ['auth', 'me'] as const

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [token, setTokenState] = useState(getToken)

  // Uygulama açılışında ve sayfa yenilendiğinde oturumu doğrula (sözleşme 3.4)
  const meQuery = useQuery({
    queryKey: ME_QUERY_KEY,
    queryFn: authApi.me,
    enabled: token !== null,
    retry: false,
    staleTime: Infinity,
  })

  const resetSession = useCallback(() => {
    clearToken()
    setTokenState(null)
    queryClient.clear()
  }, [queryClient])

  // Token'ı süresi dolmuş veya geçersiz olan her istek buraya düşer (401)
  useEffect(() => {
    setUnauthorizedHandler(() => {
      resetSession()
      toast.error('Oturumunun süresi doldu, lütfen tekrar giriş yap.')
    })
    return () => setUnauthorizedHandler(null)
  }, [resetSession])

  const signIn = useCallback(
    (response: LoginResponse) => {
      setToken(response.access_token)
      setTokenState(response.access_token)
      queryClient.setQueryData(ME_QUERY_KEY, response.user)
    },
    [queryClient],
  )

  const signOut = useCallback(async () => {
    try {
      await authApi.logout()
    } catch {
      // Backend'e ulaşılamasa bile kullanıcı yerelde çıkış yapmış olmalı
    } finally {
      resetSession()
    }
  }, [resetSession])

  const user = token ? (meQuery.data ?? null) : null

  let status: AuthStatus = 'unauthenticated'
  if (token && meQuery.isPending) status = 'loading'
  else if (user) status = 'authenticated'

  const value = useMemo<AuthContextValue>(
    () => ({ user, status, isAdmin: user?.role === 'YONETICI', signIn, signOut }),
    [user, status, signIn, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
