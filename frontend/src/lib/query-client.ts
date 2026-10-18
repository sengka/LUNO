import { MutationCache, QueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { ApiError } from '@/lib/api'

declare module '@tanstack/react-query' {
  interface Register {
    mutationMeta: {
      // 403 hatasını kendi içinde gösteren işlemler ortak uyarıyı kapatır
      skipForbiddenToast?: boolean
    }
  }
}

// US-005: Yetkisiz bir işlem denendiğinde (403) ortak uyarı mesajı (FR-012)
const mutationCache = new MutationCache({
  onError: (error, _variables, _context, mutation) => {
    if (error instanceof ApiError && error.status === 403 && !mutation.meta?.skipForbiddenToast) {
      toast.error(error.message || 'Bu işlem için yetkiniz yok.')
    }
  },
})

export const queryClient = new QueryClient({
  mutationCache,
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
})
