import type { ReactNode } from 'react'
import { Loader2Icon, SparklesIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'
import { PROVIDER_LABELS, type LLMProvider } from './types'

// US-026 · Mockup: docs/tasarim/mockup/ai-oneri-karti.png
// Toplantı notundan görev (US-051), alt görev/efor (US-052) ve özet (US-053) aynı parçaları kullanır.

// "Bunlar yalnızca öneridir" bandı (FR-078, FR-086)
export function AiNotice({ className }: { className?: string }) {
  return (
    <p className={cn('flex items-center gap-2 rounded-lg bg-secondary px-3 py-2 text-sm text-secondary-foreground', className)}>
      <SparklesIcon className="size-4 shrink-0" />
      Bunlar yalnızca öneridir. Onaylayana kadar hiçbir şey kaydedilmez.
    </p>
  )
}

interface AiSuggestionCardProps {
  title: ReactNode
  provider: LLMProvider
  children?: ReactNode
  // Düzenleme modunda butonların yerine geçen alan (ör. puan seçici)
  editing?: boolean
  onApprove: () => void
  onEdit?: () => void
  onReject: () => void
  approveDisabled?: boolean
  pending?: boolean
}

export function AiSuggestionCard({
  title,
  provider,
  children,
  editing = false,
  onApprove,
  onEdit,
  onReject,
  approveDisabled = false,
  pending = false,
}: AiSuggestionCardProps) {
  return (
    <article className="grid gap-3 rounded-xl border bg-card p-4">
      <header className="flex items-start justify-between gap-3">
        <h3 className="font-semibold text-brand">{title}</h3>
        <span className="shrink-0 rounded-md border border-primary/30 bg-secondary px-2 py-0.5 text-xs font-medium text-secondary-foreground">
          {PROVIDER_LABELS[provider] ?? provider}
        </span>
      </header>

      {children && <div className="text-sm text-muted-foreground">{children}</div>}

      <div className="flex flex-wrap justify-end gap-2">
        <Button size="sm" disabled={approveDisabled || pending} onClick={onApprove}>
          {pending && <Loader2Icon className="animate-spin" />}
          Onayla
        </Button>
        {onEdit && !editing && (
          <Button size="sm" variant="secondary" disabled={pending} onClick={onEdit}>
            Düzenle
          </Button>
        )}
        <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive" disabled={pending} onClick={onReject}>
          Reddet
        </Button>
      </div>
    </article>
  )
}

// Öneri beklenirken (mockup: "Öneriler hazırlanıyor…")
export function AiLoading() {
  return (
    <div role="status" className="grid gap-3 rounded-xl border bg-card p-4">
      <span className="text-sm font-medium text-brand">Öneriler hazırlanıyor…</span>
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-2/3" />
    </div>
  )
}

// US-026 / FR-084: Yapay zekâ çalışmasa da uygulama çalışmaya devam eder; anlaşılır mesaj gösterilir
export function AiError({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  if (error instanceof ApiError && error.code === 'RATE_LIMITED') {
    return (
      <p role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
        Çok fazla istek gönderdiniz, lütfen biraz bekleyin.
      </p>
    )
  }

  const message =
    error instanceof ApiError && error.code === 'LLM_UNAVAILABLE'
      ? 'Yapay zekâ özelliği şu an kullanılamıyor.'
      : error instanceof ApiError
        ? error.message
        : 'Yapay zekâ önerisi alınamadı.'

  return (
    <div role="alert" className="grid gap-3 rounded-xl border bg-card p-4">
      <p className="text-sm font-medium text-destructive">{message}</p>
      {onRetry && (
        <Button size="sm" variant="secondary" className="justify-self-start" onClick={onRetry}>
          Tekrar dene
        </Button>
      )}
    </div>
  )
}
