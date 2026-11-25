import type { Paginated } from '@/types/api'

// Sözleşme 2. bölüm: Notification nesnesi
export type NotificationType =
  | 'TASK_ASSIGNED'
  | 'COMMENT_ADDED'
  | 'DUE_DATE_SOON'
  | 'TASK_STALE'
  | 'TASK_PENDING_APPROVAL'
  | 'TASK_APPROVED'
  | 'TASK_REJECTED'

export interface AppNotification {
  id: number
  type: NotificationType | string
  message: string
  project_id: number | null
  task_id: number | null
  is_read: boolean
  created_at: string
}

// Sözleşme 9.1: sayfalı liste + okunmamış sayısı
export interface NotificationList extends Paginated<AppNotification> {
  unread_count: number
}
