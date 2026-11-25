import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { SparklesIcon } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/auth-context'
import { taskKeys, tasksApi } from '@/features/tasks/api'
import { STORY_POINT_OPTIONS, type StoryPoints, type Task } from '@/features/tasks/types'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'
import { aiApi } from './api'
import { AiError, AiLoading, AiNotice, AiSuggestionCard } from './AiSuggestionCard'

// US-052 (efor önerisi, sözleşme 13.4) ortak öneri kartıyla (US-026)
export function TaskPointsSuggestion({ task }: { task: Task }) {
  const { isAdmin } = useAuth()
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [chosen, setChosen] = useState<StoryPoints | null>(null)

  const suggestion = useMutation({
    mutationFn: () => aiApi.suggestPoints(task.id),
    // Hatalar kartın yerinde gösterilir
    meta: { skipForbiddenToast: true },
    onSuccess: (data) => {
      setChosen(data.story_points)
      setEditing(false)
    },
  })

  // Onaylanınca normal görev güncelleme uç noktası çağrılır (FR-078: LLM hiçbir şey kaydetmez)
  const approve = useMutation({
    mutationFn: (points: StoryPoints) => tasksApi.update(task.id, { story_points: points }),
    onSuccess: (updated) => {
      queryClient.setQueryData(taskKeys.detail(task.id), updated)
      void queryClient.invalidateQueries({ queryKey: taskKeys.board(task.project_id) })
      void queryClient.invalidateQueries({ queryKey: ['tasks', 'sprints', task.project_id] })
      toast.success(`Efor puanı ${updated.story_points} olarak kaydedildi.`)
      suggestion.reset()
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : 'Efor puanı kaydedilemedi.'),
  })

  // Sözleşme 13.4: efor önerisi yalnızca yöneticiye açık
  if (!isAdmin) return null

  const reject = () => {
    suggestion.reset()
    setEditing(false)
  }

  return (
    <section aria-label="Yapay zekâ efor önerisi" className="mt-6 grid gap-3">
      {suggestion.isIdle && (
        <Button variant="outline" className="justify-self-start" onClick={() => suggestion.mutate()}>
          <SparklesIcon />
          Yapay zekâdan efor öner
        </Button>
      )}

      {suggestion.isPending && <AiLoading />}

      {suggestion.isError && (
        <AiError error={suggestion.error} onRetry={() => suggestion.mutate()} />
      )}

      {suggestion.isSuccess && chosen !== null && (
        <>
          <AiNotice />
          <AiSuggestionCard
            title={editing ? 'Efor puanını düzenle' : `Önerilen efor: ${suggestion.data.story_points} puan`}
            provider={suggestion.data.provider}
            editing={editing}
            pending={approve.isPending}
            onApprove={() => approve.mutate(chosen)}
            onEdit={() => setEditing(true)}
            onReject={reject}
          >
            <p>{suggestion.data.reason}</p>
            {editing && (
              <div role="radiogroup" aria-label="Efor puanı" className="mt-3 flex flex-wrap gap-2">
                {STORY_POINT_OPTIONS.map((value) => (
                  <button
                    key={value}
                    type="button"
                    role="radio"
                    aria-checked={chosen === value}
                    onClick={() => setChosen(value)}
                    className={cn(
                      'flex size-9 items-center justify-center rounded-lg border text-sm font-medium transition-colors',
                      chosen === value
                        ? 'border-primary bg-secondary text-brand'
                        : 'hover:border-primary hover:text-foreground',
                    )}
                  >
                    {value}
                  </button>
                ))}
              </div>
            )}
          </AiSuggestionCard>
        </>
      )}
    </section>
  )
}
