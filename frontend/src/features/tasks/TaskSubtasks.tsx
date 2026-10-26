import { useRef, useState } from 'react'
import { Link } from 'react-router'
import { useForm } from 'react-hook-form'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { FormField } from '@/components/form/FormField'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ApiError } from '@/lib/api'
import { applyApiErrors } from '@/lib/form-errors'
import { taskKeys, tasksApi } from './api'
import type { CreateSubtaskInput, Task, TaskStatus } from './types'

const statusLabels: Record<TaskStatus, string> = {
  TODO: 'Yapılacak', IN_PROGRESS: 'Devam ediyor', REVIEW_TESTING: 'İnceleme / Test',
  DONE: 'Tamamlandı', ONAY_BEKLIYOR: 'Onay bekliyor', REDDEDILDI: 'Reddedildi',
}

export function TaskSubtasks({ task }: { task: Task }) {
  const [page, setPage] = useState(1)
  const [error, setError] = useState<string | null>(null)
  const submitting = useRef(false)
  const client = useQueryClient()
  const form = useForm<CreateSubtaskInput>({ defaultValues: { title: '' } })
  const query = useQuery({
    queryKey: taskKeys.subtasks(task.id, page),
    queryFn: () => tasksApi.listSubtasks(task.project_id, task.id, page),
    enabled: task.parent_id === null,
    retry: false,
  })
  const creation = useMutation({
    mutationFn: (input: CreateSubtaskInput) => tasksApi.createSubtask(task.id, input),
    meta: { skipForbiddenToast: true },
    onSuccess: async (created) => {
      client.setQueryData(taskKeys.detail(created.id), created)
      form.reset()
      setPage(1)
      await Promise.all([
        client.invalidateQueries({ queryKey: taskKeys.all }),
        client.invalidateQueries({ queryKey: ['projects'] }),
      ])
      toast.success(created.status === 'ONAY_BEKLIYOR' ? 'Alt görev onaya gönderildi.' : 'Alt görev eklendi.')
    },
    onError: (failure) => {
      if (failure instanceof ApiError && failure.code === 'NESTED_SUBTASK_NOT_ALLOWED') {
        setError('Alt görevlere alt görev eklenemez.')
      } else if (failure instanceof ApiError && failure.status === 403) {
        setError('Bu projeye alt görev ekleme yetkin yok.')
      } else if (failure instanceof ApiError && failure.status === 404) {
        setError('Ana görev veya proje bulunamadı.')
      } else setError(applyApiErrors(failure, form.setError, ['title']))
    },
    onSettled: () => { submitting.current = false },
  })
  const submit = (input: CreateSubtaskInput) => {
    if (submitting.current || task.parent_id !== null) return
    submitting.current = true
    setError(null)
    creation.mutate({ title: input.title.trim() })
  }
  if (task.parent_id !== null) return <p className="mt-8 text-sm text-muted-foreground">Alt görevlere alt görev eklenemez.</p>
  const progress = task.subtask_count > 0
    ? Math.min(100, Math.max(0, task.subtask_done_count / task.subtask_count * 100)) : 0
  return (
    <section className="mt-8 grid gap-4" aria-labelledby="subtasks-title">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="subtasks-title" className="text-lg font-semibold text-primary">Alt görevler</h2>
        <span className="text-sm text-muted-foreground">{task.subtask_done_count}/{task.subtask_count} tamamlandı</span>
      </div>
      <div role="progressbar" aria-label="Alt görev ilerlemesi" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress} className="h-2 overflow-hidden rounded-full bg-secondary">
        <div className="h-full bg-primary" style={{ width: `${progress}%` }} />
      </div>
      {query.isPending && <p role="status">Alt görevler yükleniyor…</p>}
      {query.isError && <div className="grid gap-2">
        <Alert variant="destructive" role="alert"><AlertDescription>{query.error instanceof ApiError ? query.error.message : 'Alt görevler alınamadı.'}</AlertDescription></Alert>
        <Button variant="outline" disabled={query.isFetching} onClick={() => void query.refetch()}>Tekrar dene</Button>
      </div>}
      {query.isSuccess && <>
        {query.data.items.length === 0 ? <p className="text-sm text-muted-foreground">Henüz alt görev yok.</p> : (
          <ul className="grid gap-3">
            {query.data.items.map((subtask) => <li key={subtask.id} className="flex flex-wrap items-start justify-between gap-2">
              <Link to={`/gorevler/${subtask.id}`} className={`min-w-0 break-words underline underline-offset-4 ${subtask.status === 'DONE' ? 'text-muted-foreground line-through' : ''}`}>{subtask.title}</Link>
              <span className="text-xs text-muted-foreground">{statusLabels[subtask.status]}</span>
            </li>)}
          </ul>
        )}
        {(page > 1 || query.data.total > query.data.limit) && <nav aria-label="Alt görev sayfaları" className="flex items-center justify-between gap-2">
          <Button variant="outline" disabled={page === 1 || query.isFetching} onClick={() => setPage(page - 1)}>Önceki</Button>
          <span className="text-sm">Sayfa {page}</span>
          <Button variant="outline" disabled={page * query.data.limit >= query.data.total || query.isFetching} onClick={() => setPage(page + 1)}>Sonraki</Button>
        </nav>}
      </>}
      <form onSubmit={(event) => void form.handleSubmit(submit)(event)} noValidate className="grid gap-3">
        <fieldset disabled={creation.isPending}>
          <FormField id="subtask-title" label="Yeni alt görev" error={form.formState.errors.title?.message}>
            <Input id="subtask-title" aria-invalid={!!form.formState.errors.title} aria-describedby={form.formState.errors.title ? 'subtask-title-error' : undefined}
              {...form.register('title', { validate: (value) => value.trim().length >= 2 && value.trim().length <= 200 || 'Alt görev başlığı 2–200 karakter olmalıdır.' })} />
          </FormField>
        </fieldset>
        {error && <Alert variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}
        <Button type="submit" className="justify-self-start" disabled={creation.isPending}>{creation.isPending ? 'Ekleniyor…' : 'Alt görev ekle'}</Button>
      </form>
    </section>
  )
}
