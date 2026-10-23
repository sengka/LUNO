import { useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { FormField } from '@/components/form/FormField'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { ApiError } from '@/lib/api'
import { applyApiErrors } from '@/lib/form-errors'
import { taskKeys, tasksApi } from './api'
import type { Task, UpdateTaskInput } from './types'

interface Values { title: string; description: string; start_date: string; due_date: string }
const fields = ['title', 'description', 'start_date', 'due_date'] as const

export function TaskEditForm({ task, onClose }: { task: Task; onClose: () => void }) {
  const client = useQueryClient()
  // Arka plan sorgusu yenilense de yalnızca kullanıcının değiştirdiği alanları gönder.
  const [initialTask] = useState(task)
  const submitting = useRef(false)
  const [error, setError] = useState<string | null>(null)
  const form = useForm<Values>({ defaultValues: {
    title: task.title, description: task.description ?? '',
    start_date: task.start_date ?? '', due_date: task.due_date ?? '',
  } })
  const mutation = useMutation({
    mutationFn: (input: UpdateTaskInput) => tasksApi.update(task.id, input),
    meta: { skipForbiddenToast: true },
    onSuccess: async (updated) => {
      await client.cancelQueries({ queryKey: taskKeys.detail(task.id), exact: true })
      client.setQueryData(taskKeys.detail(task.id), updated)
      void client.invalidateQueries({ queryKey: taskKeys.all, predicate: (query) =>
        !(query.queryKey[1] === 'detail' && query.queryKey[2] === task.id),
      })
      void client.invalidateQueries({ queryKey: ['projects'] })
      toast.success('Görev güncellendi.')
      onClose()
    },
    onError: (failure) => {
      if (failure instanceof ApiError && failure.code === 'INVALID_DATE_RANGE') {
        form.setError('due_date', { message: 'Teslim tarihi başlangıç tarihinden önce olamaz.' }, { shouldFocus: true })
      } else if (failure instanceof ApiError && failure.status === 403) {
        setError('Bu görevi düzenleme yetkin yok.')
      } else if (failure instanceof ApiError && failure.status === 404) {
        setError('Görev bulunamadı. Daha önce silinmiş olabilir.')
      } else {
        setError(applyApiErrors(failure, form.setError, fields))
      }
    },
    onSettled: () => { submitting.current = false },
  })
  const submit = (values: Values) => {
    if (submitting.current) return
    setError(null)
    const changes: UpdateTaskInput = {}
    if (values.title.trim() !== initialTask.title) changes.title = values.title.trim()
    if (values.description !== (initialTask.description ?? '')) changes.description = values.description || null
    if (values.start_date !== (initialTask.start_date ?? '')) changes.start_date = values.start_date || null
    if (values.due_date !== (initialTask.due_date ?? '')) changes.due_date = values.due_date || null
    const startDate = changes.start_date === undefined ? task.start_date : changes.start_date
    const dueDate = changes.due_date === undefined ? task.due_date : changes.due_date
    if (startDate && dueDate && dueDate < startDate) {
      form.setError('due_date', { message: 'Teslim tarihi başlangıç tarihinden önce olamaz.' }, { shouldFocus: true })
      return
    }
    if (!Object.keys(changes).length) { onClose(); return }
    submitting.current = true
    mutation.mutate(changes)
  }
  return (
    <form onSubmit={(event) => void form.handleSubmit(submit)(event)} noValidate className="grid gap-5" aria-label="Görevi düzenle">
      <h2 className="text-lg font-semibold">Görevi düzenle</h2>
      <fieldset disabled={mutation.isPending} className="grid gap-5">
        <FormField id="task-title" label="Başlık" error={form.formState.errors.title?.message}>
          <Input id="task-title" aria-invalid={!!form.formState.errors.title} aria-describedby={form.formState.errors.title ? 'task-title-error' : undefined}
            {...form.register('title', { validate: (value) => {
              const title = value.trim()
              return title.length >= 2 && title.length <= 200 || 'Görev başlığı 2–200 karakter olmalıdır.'
            } })} />
        </FormField>
        <FormField id="task-description" label="Açıklama" error={form.formState.errors.description?.message}>
          <Textarea id="task-description" rows={6} aria-invalid={!!form.formState.errors.description} aria-describedby={form.formState.errors.description ? 'task-description-error' : undefined} {...form.register('description')} />
        </FormField>
        <div className="grid gap-5 sm:grid-cols-2">
          {(['start_date', 'due_date'] as const).map((field) => (
            <FormField key={field} id={`task-${field}`} label={field === 'start_date' ? 'Başlangıç tarihi' : 'Teslim tarihi'} error={form.formState.errors[field]?.message}>
              <Input id={`task-${field}`} type="date" aria-invalid={!!form.formState.errors[field]} aria-describedby={form.formState.errors[field] ? `task-${field}-error` : undefined} {...form.register(field)} />
            </FormField>
          ))}
        </div>
      </fieldset>
      {error && <Alert variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" disabled={mutation.isPending} onClick={onClose}>Vazgeç</Button>
        <Button type="submit" disabled={mutation.isPending || !form.formState.isDirty}>{mutation.isPending ? 'Kaydediliyor…' : 'Kaydet'}</Button>
      </div>
    </form>
  )
}
