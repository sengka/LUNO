import { cn } from '@/lib/utils'
import { formatRelative, notificationStyle } from './notification-utils'
import type { AppNotification } from './types'

interface NotificationItemProps {
  notification: AppNotification
  projectName: string | null
  onOpen: (notification: AppNotification) => void
  compact?: boolean
}

// Mockup: docs/tasarim/mockup/bildirimler.png (liste satırı ve zil paneli)
export function NotificationItem({ notification, projectName, onOpen, compact = false }: NotificationItemProps) {
  const style = notificationStyle(notification.type)
  const unread = !notification.is_read

  return (
    <button
      type="button"
      onClick={() => onOpen(notification)}
      className={cn(
        'flex w-full items-start gap-3 text-left transition-colors hover:bg-muted/60 focus-visible:outline-2 focus-visible:outline-ring',
        compact ? 'px-4 py-3' : 'px-5 py-4',
        unread && 'bg-secondary/40',
      )}
    >
      <span
        className={cn(
          'flex shrink-0 items-center justify-center rounded-lg',
          compact ? 'size-8' : 'size-10',
          style.className,
        )}
      >
        <style.icon className={compact ? 'size-4' : 'size-5'} />
      </span>

      <span className="grid min-w-0 flex-1 gap-1">
        <span className={cn('break-words text-sm', unread && 'font-semibold')}>{notification.message}</span>
        <span className="flex flex-wrap items-center gap-x-1.5 text-xs text-muted-foreground">
          {projectName && (
            <>
              <span className="truncate">{projectName}</span>·
            </>
          )}
          <time dateTime={notification.created_at}>{formatRelative(notification.created_at)}</time>
        </span>
      </span>

      {unread && (
        <span className="mt-1.5 size-2 shrink-0 rounded-full bg-primary">
          <span className="sr-only">Okunmamış</span>
        </span>
      )}
    </button>
  )
}
