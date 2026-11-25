import { useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { BellOffIcon, CheckCheckIcon, Loader2Icon } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'
import { notificationKeys, notificationsApi } from './api'
import { useMarkAllRead, useOpenNotification, useProjectNames } from './hooks'
import { NotificationItem } from './NotificationItem'

const PAGE_SIZE = 20

type Tab = 'all' | 'unread'

// US-021 · Mockup: docs/tasarim/mockup/bildirimler.png
export function NotificationsPage() {
  const [tab, setTab] = useState<Tab>('all')
  const [page, setPage] = useState(1)
  const openNotification = useOpenNotification()
  const markAllRead = useMarkAllRead()
  const projectName = useProjectNames()

  const unreadOnly = tab === 'unread'
  const listQuery = useQuery({
    queryKey: notificationKeys.list(unreadOnly, page),
    queryFn: () => notificationsApi.list({ unreadOnly, page, limit: PAGE_SIZE }),
    placeholderData: keepPreviousData,
  })

  const data = listQuery.data
  const unread = data?.unread_count ?? 0
  // "Tümü" sekmesinde total tüm bildirimleri verir; okunmuş sayısı oradan hesaplanır
  const totalAll = tab === 'all' ? data?.total : undefined
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1

  const changeTab = (next: Tab) => {
    setTab(next)
    setPage(1)
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_18rem]">
      <div className="grid content-start gap-6">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div className="grid gap-1">
            <h1 className="text-2xl font-semibold text-brand">Bildirimler</h1>
            <p className="text-sm text-muted-foreground">Görevlerinle ve yorumlarla ilgili güncellemeler.</p>
          </div>
          <Button
            variant="secondary"
            disabled={unread === 0 || markAllRead.isPending}
            onClick={() => markAllRead.mutate()}
          >
            {markAllRead.isPending ? <Loader2Icon className="animate-spin" /> : <CheckCheckIcon />}
            Tümünü okundu işaretle
          </Button>
        </header>

        <div role="tablist" aria-label="Bildirim filtresi" className="flex gap-1 border-b">
          {(
            [
              ['all', 'Tümü'],
              ['unread', `Okunmamış (${unread})`],
            ] as const
          ).map(([value, label]) => (
            <button
              key={value}
              type="button"
              role="tab"
              aria-selected={tab === value}
              onClick={() => changeTab(value)}
              className={cn(
                '-mb-px border-b-2 px-3 pb-3 text-sm font-medium transition-colors',
                tab === value
                  ? 'border-primary text-brand'
                  : 'border-transparent text-muted-foreground hover:text-foreground',
              )}
            >
              {label}
            </button>
          ))}
        </div>

        <section className="overflow-hidden rounded-xl border bg-card" aria-live="polite">
          {listQuery.isPending ? (
            <div className="grid gap-5 p-5" role="status" aria-label="Bildirimler yükleniyor">
              {[0, 1, 2].map((key) => (
                <div key={key} className="flex gap-3">
                  <Skeleton className="size-10 rounded-lg" />
                  <div className="grid flex-1 gap-2">
                    <Skeleton className="h-3.5 w-3/4" />
                    <Skeleton className="h-3 w-1/3" />
                  </div>
                </div>
              ))}
            </div>
          ) : listQuery.isError ? (
            <div className="grid gap-3 p-5">
              <Alert variant="destructive">
                <AlertDescription>
                  {listQuery.error instanceof ApiError ? listQuery.error.message : 'Bildirimler alınamadı.'}
                </AlertDescription>
              </Alert>
              <Button variant="outline" className="justify-self-start" onClick={() => void listQuery.refetch()}>
                Tekrar dene
              </Button>
            </div>
          ) : data && data.items.length === 0 ? (
            <div className="grid justify-items-center gap-3 px-6 py-14 text-center">
              <span className="flex size-12 items-center justify-center rounded-full bg-secondary text-primary">
                <BellOffIcon className="size-6" />
              </span>
              <h2 className="font-semibold text-brand">
                {unreadOnly ? 'Okunmamış bildirimin yok' : 'Hiç bildirimin yok'}
              </h2>
              <p className="text-sm text-muted-foreground">Yeni gelişmeler burada görünür.</p>
            </div>
          ) : (
            <>
              <ul className="divide-y">
                {data?.items.map((notification) => (
                  <li key={notification.id}>
                    <NotificationItem
                      notification={notification}
                      projectName={projectName(notification.project_id)}
                      onOpen={openNotification}
                    />
                  </li>
                ))}
              </ul>
              <footer className="flex flex-wrap items-center justify-between gap-3 border-t px-5 py-3 text-xs text-muted-foreground">
                <span>
                  {data?.total} bildirimden {data?.items.length} tanesi gösteriliyor
                </span>
                {totalPages > 1 && (
                  <span className="flex items-center gap-2">
                    <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                      Önceki
                    </Button>
                    {page} / {totalPages}
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page >= totalPages}
                      onClick={() => setPage((p) => p + 1)}
                    >
                      Sonraki
                    </Button>
                  </span>
                )}
              </footer>
            </>
          )}
        </section>
      </div>

      <aside className="grid content-start gap-4 rounded-xl border bg-card p-5" aria-label="Bildirim özeti">
        <h2 className="font-semibold text-brand">Bir bakışta</h2>
        <dl className="grid gap-3 text-sm">
          <div className="flex justify-between">
            <dt className="text-muted-foreground">Okunmamış bildirim</dt>
            <dd className="font-semibold text-brand">{unread}</dd>
          </div>
          {totalAll !== undefined && (
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Okunmuş bildirim</dt>
              <dd className="font-semibold">{totalAll - unread}</dd>
            </div>
          )}
        </dl>
      </aside>
    </div>
  )
}
