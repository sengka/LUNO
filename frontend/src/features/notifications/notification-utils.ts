import {
  BellIcon,
  CircleCheckIcon,
  CircleXIcon,
  ClockIcon,
  HourglassIcon,
  MessageSquareIcon,
  TriangleAlertIcon,
  UserPlusIcon,
  type LucideIcon,
} from 'lucide-react'
import type { AppNotification } from './types'

interface NotificationStyle {
  icon: LucideIcon
  className: string
}

// Mockup'taki tür ikonları ve renkleri (docs/tasarim/mockup/bildirimler.png)
export function notificationStyle(type: string): NotificationStyle {
  switch (type) {
    case 'TASK_ASSIGNED':
      return { icon: UserPlusIcon, className: 'bg-secondary text-primary' }
    case 'COMMENT_ADDED':
      return { icon: MessageSquareIcon, className: 'bg-secondary text-primary' }
    case 'DUE_DATE_SOON':
      return { icon: TriangleAlertIcon, className: 'bg-amber-50 text-amber-600' }
    case 'TASK_STALE':
      return { icon: ClockIcon, className: 'bg-secondary text-primary' }
    case 'TASK_PENDING_APPROVAL':
      return { icon: HourglassIcon, className: 'bg-amber-50 text-amber-600' }
    case 'TASK_APPROVED':
      return { icon: CircleCheckIcon, className: 'bg-emerald-50 text-emerald-600' }
    case 'TASK_REJECTED':
      return { icon: CircleXIcon, className: 'bg-red-50 text-red-500' }
    default:
      return { icon: BellIcon, className: 'bg-muted text-muted-foreground' }
  }
}

const rtf = new Intl.RelativeTimeFormat('tr', { numeric: 'auto' })
const dateFormatter = new Intl.DateTimeFormat('tr-TR', { day: 'numeric', month: 'short' })

// "Az önce", "10 dakika önce", "2 saat önce", "dün", "7 Eki"
export function formatRelative(value: string, now = new Date()) {
  const date = new Date(value)
  const seconds = Math.round((date.getTime() - now.getTime()) / 1000)
  const abs = Math.abs(seconds)
  if (abs < 60) return 'Az önce'
  if (abs < 3600) return rtf.format(Math.round(seconds / 60), 'minute')
  if (abs < 86400) return rtf.format(Math.round(seconds / 3600), 'hour')
  if (abs < 7 * 86400) return rtf.format(Math.round(seconds / 86400), 'day')
  return dateFormatter.format(date)
}

// Bildirime tıklayınca gidilecek yer: görev varsa görev detayı, yoksa proje
export function notificationTarget(notification: AppNotification) {
  if (notification.task_id) return `/gorevler/${notification.task_id}`
  if (notification.project_id) return `/projeler/${notification.project_id}`
  return null
}
