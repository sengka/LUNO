import { api } from '@/lib/api'
import type { Paginated } from '@/types/api'
import type { AppNotification, NotificationList } from './types'

export const notificationKeys = {
  all: ['notifications'] as const,
  preview: ['notifications', 'preview'] as const,
  list: (unreadOnly: boolean, page: number) => ['notifications', 'list', { unreadOnly, page }] as const,
}

// Sözleşme 9.1 – 9.3
export const notificationsApi = {
  list: ({ unreadOnly = false, page = 1, limit = 20 }: { unreadOnly?: boolean; page?: number; limit?: number }) =>
    api.get<NotificationList>(`/notifications?unread_only=${unreadOnly}&page=${page}&limit=${limit}`),
  markRead: (id: number) => api.patch<AppNotification>(`/notifications/${id}/read`),
  markAllRead: () => api.post<void>('/notifications/read-all'),
  // Bildirimde yalnızca project_id var; adını göstermek için kullanıcının projeleri bir kez çekilir
  projectNames: () => api.get<Paginated<{ id: number; name: string }>>('/projects?page=1&limit=100'),
}
