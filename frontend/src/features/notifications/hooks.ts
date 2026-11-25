import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'
import { ApiError } from '@/lib/api'
import { notificationKeys, notificationsApi } from './api'
import { notificationTarget } from './notification-utils'
import type { AppNotification } from './types'

// Okundu bilgisi değişince zil, liste ve kontrol panelindeki sayı birlikte güncellensin
function useRefreshNotifications() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: notificationKeys.all })
    void queryClient.invalidateQueries({ queryKey: ['tasks', 'dashboard'] })
  }
}

// Bildirime tıklanınca: okunmamışsa okundu yap, ilgili göreve/projeye git
export function useOpenNotification() {
  const navigate = useNavigate()
  const refresh = useRefreshNotifications()

  const markRead = useMutation({
    mutationFn: notificationsApi.markRead,
    onSuccess: refresh,
  })

  return (notification: AppNotification) => {
    if (!notification.is_read) markRead.mutate(notification.id)
    const target = notificationTarget(notification)
    if (target) navigate(target)
  }
}

// Sözleşme 9.3
export function useMarkAllRead() {
  const refresh = useRefreshNotifications()
  return useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: () => {
      refresh()
      toast.success('Tüm bildirimler okundu olarak işaretlendi.')
    },
    onError: (error) => {
      toast.error(error instanceof ApiError ? error.message : 'Bildirimler güncellenemedi.')
    },
  })
}

// project_id → proje adı. 5 dakika önbellekte tutulur, her bildirim için ayrı istek atılmaz.
export function useProjectNames() {
  const query = useQuery({
    queryKey: ['projects', 'names'],
    queryFn: notificationsApi.projectNames,
    staleTime: 5 * 60 * 1000,
  })
  const names = new Map(query.data?.items.map((project) => [project.id, project.name]))
  return (projectId: number | null) => (projectId === null ? null : (names.get(projectId) ?? null))
}
