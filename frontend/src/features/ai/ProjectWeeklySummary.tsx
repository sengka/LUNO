import { useMutation } from '@tanstack/react-query'
import { RefreshCwIcon, SparklesIcon, XIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/auth-context'
import { aiApi } from './api'
import { AiError, AiLoading, AiNotice } from './AiSuggestionCard'
import { PROVIDER_LABELS } from './types'

function formatShortDate(value: string) {
  const date = new Date(`${value}T00:00:00`)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('tr-TR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(date)
}

// US-053 / FR-081 (sözleşme 13.5): Haftalık proje özeti (yalnızca yönetici)
export function ProjectWeeklySummary({ projectId }: { projectId: number }) {
  const { isAdmin } = useAuth()

  const summary = useMutation({
    mutationFn: () => aiApi.weeklySummary(projectId),
    meta: { skipForbiddenToast: true },
  })

  if (!isAdmin) return null

  return (
    <section aria-label="Haftalık proje özeti" className="grid gap-3">
      {summary.isIdle && (
        <Button variant="outline" className="justify-self-start" onClick={() => summary.mutate()}>
          <SparklesIcon className="size-4" />
          Haftalık özet oluştur
        </Button>
      )}

      {summary.isPending && <AiLoading />}

      {summary.isError && <AiError error={summary.error} onRetry={() => summary.mutate()} />}

      {summary.isSuccess && (
        <>
          <AiNotice />
          <article className="grid gap-3 rounded-xl border bg-card p-5">
            <header className="flex flex-wrap items-start justify-between gap-3">
              <div className="grid gap-0.5">
                <h3 className="font-semibold text-brand">Haftalık proje özeti</h3>
                <p className="text-xs text-muted-foreground">
                  {formatShortDate(summary.data.from)} – {formatShortDate(summary.data.to)}
                </p>
              </div>
              <span className="shrink-0 rounded-md border border-primary/30 bg-secondary px-2 py-0.5 text-xs font-medium text-secondary-foreground">
                {PROVIDER_LABELS[summary.data.provider] ?? summary.data.provider}
              </span>
            </header>

            <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
              {summary.data.summary}
            </p>

            <div className="flex flex-wrap justify-end gap-2">
              <Button size="sm" variant="secondary" onClick={() => summary.mutate()}>
                <RefreshCwIcon className="size-3.5" />
                Yeniden oluştur
              </Button>
              <Button size="sm" variant="ghost" onClick={() => summary.reset()}>
                <XIcon className="size-3.5" />
                Kapat
              </Button>
            </div>
          </article>
        </>
      )}
    </section>
  )
}
