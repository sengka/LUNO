import { useMutation } from '@tanstack/react-query'
import { RefreshCwIcon, SparklesIcon, XIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { aiApi } from './api'
import { AiError, AiLoading, AiNotice } from './AiSuggestionCard'
import { PROVIDER_LABELS } from './types'

// US-053 / FR-082 (sözleşme 13.6): Yorum zinciri özeti (proje üyesi)
export function TaskCommentSummary({ taskId }: { taskId: number }) {
  const summary = useMutation({
    mutationFn: () => aiApi.summarizeComments(taskId),
    meta: { skipForbiddenToast: true },
  })

  return (
    <section aria-label="Yorum zinciri özeti" className="mt-6 grid gap-3">
      {summary.isIdle && (
        <Button variant="outline" size="sm" className="justify-self-start" onClick={() => summary.mutate()}>
          <SparklesIcon className="size-4" />
          Yorumları özetle
        </Button>
      )}

      {summary.isPending && <AiLoading />}

      {summary.isError && <AiError error={summary.error} onRetry={() => summary.mutate()} />}

      {summary.isSuccess && (
        <>
          <AiNotice />
          <article className="grid gap-4 rounded-xl border bg-card p-4">
            <header className="flex items-start justify-between gap-3">
              <h3 className="font-semibold text-brand">Yorum zinciri özeti</h3>
              <span className="shrink-0 rounded-md border border-primary/30 bg-secondary px-2 py-0.5 text-xs font-medium text-secondary-foreground">
                {PROVIDER_LABELS[summary.data.provider] ?? summary.data.provider}
              </span>
            </header>

            <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
              {summary.data.summary}
            </p>

            {summary.data.decisions.length > 0 && (
              <div className="grid gap-1.5">
                <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Alınan kararlar
                </h4>
                <ul className="list-disc space-y-1 pl-5 text-sm text-foreground">
                  {summary.data.decisions.map((decision, idx) => (
                    <li key={idx}>{decision}</li>
                  ))}
                </ul>
              </div>
            )}

            {summary.data.open_questions.length > 0 && (
              <div className="grid gap-1.5">
                <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Açık sorular
                </h4>
                <ul className="list-disc space-y-1 pl-5 text-sm text-foreground">
                  {summary.data.open_questions.map((question, idx) => (
                    <li key={idx}>{question}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="flex flex-wrap justify-end gap-2">
              <Button size="sm" variant="secondary" onClick={() => summary.mutate()}>
                <RefreshCwIcon className="size-3.5" />
                Yeniden özetle
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
