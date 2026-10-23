import { useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { FormField } from '@/components/form/FormField'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAuth } from '@/features/auth/auth-context'
import { ApiError } from '@/lib/api'
import { applyApiErrors } from '@/lib/form-errors'
import { taskKeys, tasksApi } from './api'
import type { CreateLabelInput, Label, Task } from './types'

export function TaskLabels({ task }: { task: Task }) {
  const { isAdmin } = useAuth()
  const client = useQueryClient()
  const [createError, setCreateError] = useState<string | null>(null)
  const [attachError, setAttachError] = useState<string | null>(null)
  const creating = useRef(false)
  const attaching = useRef(false)
  const createForm = useForm<CreateLabelInput>({ defaultValues: { name: '', color: '' } })
  const attachForm = useForm<{ label_ids: string }>({ defaultValues: { label_ids: '' } })
  const labels = useQuery({ queryKey: taskKeys.labels(task.project_id), queryFn: () => tasksApi.listLabels(task.project_id), retry: false })
  const available = (labels.data ?? []).filter((label) => !task.labels.some((assigned) => assigned.id === label.id))
  const creation = useMutation({
    mutationFn: (input: CreateLabelInput) => tasksApi.createLabel(task.project_id, input),
    meta: { skipForbiddenToast: true },
    onSuccess: async (created) => {
      await client.cancelQueries({ queryKey: taskKeys.labels(task.project_id), exact: true })
      client.setQueryData<Label[]>(taskKeys.labels(task.project_id), (current) =>
        [...(current ?? []).filter((label) => label.id !== created.id), created])
      createForm.reset()
      void client.invalidateQueries({ queryKey: taskKeys.labels(task.project_id), exact: true })
      toast.success('Proje etiketi oluşturuldu.')
    },
    onError: (failure) => {
      if (failure instanceof ApiError && failure.code === 'LABEL_EXISTS') {
        createForm.setError('name', { message: 'Bu etiket zaten var.' }, { shouldFocus: true })
      } else if (failure instanceof ApiError && failure.status === 403) {
        setCreateError('Bu projede etiket oluşturma yetkin yok.')
      } else setCreateError(applyApiErrors(failure, createForm.setError, ['name', 'color']))
    },
    onSettled: () => { creating.current = false },
  })
  const attachment = useMutation({
    // 6.4 label_ids alanını günceller: mevcut etiketleri koruyarak yeni etiketi ekle.
    mutationFn: (labelId: number) => tasksApi.update(task.id, {
      label_ids: [...new Set([...task.labels.map((label) => label.id), labelId])],
    }),
    meta: { skipForbiddenToast: true },
    onSuccess: async (updated) => {
      await client.cancelQueries({ queryKey: taskKeys.detail(task.id), exact: true })
      client.setQueryData(taskKeys.detail(task.id), updated)
      attachForm.reset()
      void client.invalidateQueries({ queryKey: taskKeys.all, predicate: (query) =>
        !(query.queryKey[1] === 'detail' && query.queryKey[2] === task.id),
      })
      void client.invalidateQueries({ queryKey: ['projects'] })
      toast.success('Etiket göreve eklendi.')
    },
    onError: (failure) => {
      if (failure instanceof ApiError && failure.status === 403) {
        setAttachError('Göreve etiket eklemek için yönetici olmalısın ve projenin üyesi olmalısın.')
      } else if (failure instanceof ApiError && failure.status === 404) {
        setAttachError('Görev veya etiket bulunamadı.')
      } else setAttachError(applyApiErrors(failure, attachForm.setError, ['label_ids']))
    },
    onSettled: () => { attaching.current = false },
  })
  const create = (input: CreateLabelInput) => {
    if (creating.current) return
    creating.current = true
    setCreateError(null)
    creation.mutate({ name: input.name.trim(), color: input.color.trim() })
  }
  const attach = ({ label_ids }: { label_ids: string }) => {
    if (attaching.current || !isAdmin) return
    const id = Number(label_ids)
    if (!available.some((label) => label.id === id)) {
      attachForm.setError('label_ids', { message: 'Eklenecek bir etiket seçin.' })
      return
    }
    attaching.current = true
    setAttachError(null)
    attachment.mutate(id)
  }
  return (
    <section className="mt-6 grid gap-4" aria-labelledby="task-labels-title">
      <h3 id="task-labels-title" className="font-semibold text-primary">Etiketler</h3>
      {task.labels.length === 0 ? <p className="text-sm text-muted-foreground">Bu göreve etiket eklenmemiş.</p> : (
        <ul className="flex flex-wrap gap-2">{task.labels.map((label) => <li key={label.id}>
          <Badge variant="secondary" className="h-auto max-w-full whitespace-normal break-words">
            <span aria-hidden="true" className="size-2 shrink-0 rounded-full" style={{ backgroundColor: label.color }} />{label.name}
          </Badge>
        </li>)}</ul>
      )}
      {labels.isPending && <p role="status">Proje etiketleri yükleniyor…</p>}
      {labels.isError && <div className="grid gap-2">
        <Alert variant="destructive" role="alert"><AlertDescription>{labels.error instanceof ApiError ? labels.error.message : 'Proje etiketleri alınamadı.'}</AlertDescription></Alert>
        <Button variant="outline" disabled={labels.isFetching} onClick={() => void labels.refetch()}>Tekrar dene</Button>
      </div>}
      {labels.isSuccess && labels.data.length === 0 && <p className="text-sm text-muted-foreground">Projede henüz etiket yok.</p>}
      {isAdmin && labels.isSuccess && available.length > 0 && <form onSubmit={(event) => void attachForm.handleSubmit(attach)(event)} noValidate className="grid gap-3">
        <fieldset disabled={attachment.isPending}>
          <FormField id="task-label-ids" label="Mevcut etiketi ekle" error={attachForm.formState.errors.label_ids?.message}>
            <select id="task-label-ids" className="w-full rounded-md border bg-background px-3 py-2 text-sm" aria-invalid={!!attachForm.formState.errors.label_ids} aria-describedby={attachForm.formState.errors.label_ids ? 'task-label-ids-error' : undefined}
              {...attachForm.register('label_ids', { required: 'Eklenecek bir etiket seçin.' })}>
              <option value="">Etiket seçin</option>
              {available.map((label) => <option key={label.id} value={label.id}>{label.name}</option>)}
            </select>
          </FormField>
        </fieldset>
        <Button type="submit" disabled={attachment.isPending}>{attachment.isPending ? 'Ekleniyor…' : 'Göreve ekle'}</Button>
      </form>}
      {isAdmin && labels.isSuccess && labels.data.length > 0 && available.length === 0 && <p className="text-sm text-muted-foreground">Tüm proje etiketleri bu göreve eklenmiş.</p>}
      {attachError && <Alert variant="destructive" role="alert"><AlertDescription>{attachError}</AlertDescription></Alert>}
      <form onSubmit={(event) => void createForm.handleSubmit(create)(event)} noValidate className="grid gap-3 border-t pt-4">
        <h4 className="text-sm font-medium">Proje etiketi oluştur</h4>
        <fieldset disabled={creation.isPending} className="grid gap-3">
          <FormField id="label-name" label="Etiket adı" error={createForm.formState.errors.name?.message}>
            <Input id="label-name" aria-invalid={!!createForm.formState.errors.name} aria-describedby={createForm.formState.errors.name ? 'label-name-error' : undefined}
              {...createForm.register('name', { validate: (value) => !!value.trim() || 'Etiket adı girin.' })} />
          </FormField>
          <FormField id="label-color" label="Renk" hint="Örnek: #3A4CA0" error={createForm.formState.errors.color?.message}>
            <Input id="label-color" placeholder="#3A4CA0" aria-invalid={!!createForm.formState.errors.color} aria-describedby={createForm.formState.errors.color ? 'label-color-error' : undefined}
              {...createForm.register('color', { validate: (value) => !!value.trim() || 'Etiket rengi girin.' })} />
          </FormField>
        </fieldset>
        {createError && <Alert variant="destructive" role="alert"><AlertDescription>{createError}</AlertDescription></Alert>}
        <Button type="submit" disabled={creation.isPending}>{creation.isPending ? 'Oluşturuluyor…' : 'Etiket oluştur'}</Button>
      </form>
    </section>
  )
}
