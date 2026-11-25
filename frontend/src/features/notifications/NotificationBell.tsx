import { useState } from 'react'
import { Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { ArrowRightIcon, BellIcon, BellOffIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Skeleton } from '@/components/ui/skeleton'
import { notificationKeys, notificationsApi } from './api'
import { useOpenNotification, useProjectNames } from './hooks'
import { NotificationItem } from './NotificationItem'
import type { AppNotification } from './types'

const PREVIEW_LIMIT = 5
// Sözleşme 9.1: zil 30 saniyede bir güncellenir (sekme açıkken)
const POLL_INTERVAL = 30_000

// US-021 · Mockup: docs/tasarim/mockup/bildirimler.png (üst bardaki zil ve açılır panel)
export function NotificationBell() {
  const [open, setOpen] = useState(false)
  const openNotification = useOpenNotification()
  const projectName = useProjectNames()

  const previewQuery = useQuery({
    queryKey: notificationKeys.preview,
    queryFn: () => notificationsApi.list({ limit: PREVIEW_LIMIT }),
    refetchInterval: POLL_INTERVAL,
    refetchIntervalInBackground: false,
  })

  const unread = previewQuery.data?.unread_count ?? 0
  const items = previewQuery.data?.items ?? []

  const handleOpen = (notification: AppNotification) => {
    setOpen(false)
    openNotification(notification)
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          aria-label={unread > 0 ? `Bildirimler, ${unread} okunmamış` : 'Bildirimler'}
        >
          <BellIcon />
          {unread > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-semibold text-primary-foreground">
              {unread > 99 ? '99+' : unread}
            </span>
          )}
        </Button>
      </PopoverTrigger>

      <PopoverContent align="end" className="w-[min(24rem,calc(100vw-2rem))] gap-0 overflow-hidden p-0">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h2 className="font-semibold text-brand">Bildirimler</h2>
          {unread > 0 && (
            <span className="rounded-full bg-secondary px-2 py-0.5 text-xs font-medium text-secondary-foreground">
              {unread} okunmamış
            </span>
          )}
        </div>

        <div className="max-h-96 overflow-y-auto">
          {previewQuery.isPending ? (
            <div className="grid gap-3 p-4" role="status" aria-label="Bildirimler yükleniyor">
              {[0, 1, 2].map((key) => (
                <div key={key} className="flex gap-3">
                  <Skeleton className="size-8 rounded-lg" />
                  <div className="grid flex-1 gap-2">
                    <Skeleton className="h-3 w-4/5" />
                    <Skeleton className="h-3 w-1/3" />
                  </div>
                </div>
              ))}
            </div>
          ) : previewQuery.isError ? (
            <p className="p-4 text-sm text-destructive">Bildirimler alınamadı.</p>
          ) : items.length === 0 ? (
            <p className="flex items-center gap-2 p-4 text-sm text-muted-foreground">
              <BellOffIcon className="size-4" />
              Hiç bildirimin yok.
            </p>
          ) : (
            <ul className="divide-y">
              {items.map((notification) => (
                <li key={notification.id}>
                  <NotificationItem
                    notification={notification}
                    projectName={projectName(notification.project_id)}
                    onOpen={handleOpen}
                    compact
                  />
                </li>
              ))}
            </ul>
          )}
        </div>

        <Link
          to="/bildirimler"
          onClick={() => setOpen(false)}
          className="flex items-center justify-center gap-2 border-t px-4 py-3 text-sm font-medium text-brand hover:bg-muted/60"
        >
          Tüm bildirimleri gör
          <ArrowRightIcon className="size-4" />
        </Link>
      </PopoverContent>
    </Popover>
  )
}
