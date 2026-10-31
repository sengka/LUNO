import { useState, type ReactNode } from 'react'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { z } from 'zod'
import { CircleAlertIcon, Loader2Icon } from 'lucide-react'
import { toast } from 'sonner'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { FormField } from '@/components/form/FormField'
import { ApiError } from '@/lib/api'
import { applyApiErrors } from '@/lib/form-errors'
import { taskKeys, tasksApi } from './api'
import { AssigneeSelect } from './AssigneeSelect'
import { PRIORITY_LABELS, STORY_POINT_OPTIONS } from './types'

const DATE_RANGE_MESSAGE = 'Teslim tarihi başlangıç tarihinden önce olamaz.'

// Kurallar sözleşme 6.2 ile aynı (FR-024, FR-025)
const createTaskSchema = z
  .object({
    title: z
      .string()
      .trim()
      .min(2, { error: 'Görev başlığı en az 2 karakter olmalıdır.' })
      .max(200, { error: 'Görev başlığı en fazla 200 karakter olabilir.' }),
    description: z.string().trim().max(5000, { error: 'Açıklama çok uzun.' }),
    start_date: z.string(),
    due_date: z.string(),
    assignee_id: z.number().nullable(),
    priority: z.enum(['DUSUK', 'ORTA', 'YUKSEK'], { error: 'Geçerli bir öncelik seçin.' }).nullable(),
    story_points: z.union([z.literal(1), z.literal(2), z.literal(3), z.literal(5), z.literal(8), z.literal(13)], {
      error: 'Efor puanı 1, 2, 3, 5, 8 veya 13 olmalıdır.',
    }).nullable(),
  })
  // YYYY-MM-DD biçimindeki tarihler metin olarak da doğru sıralanır
  .refine((values) => !values.start_date || !values.due_date || values.due_date >= values.start_date, {
    path: ['due_date'],
    error: DATE_RANGE_MESSAGE,
  })

type CreateTaskValues = z.infer<typeof createTaskSchema>

const FIELDS = ['title', 'description', 'start_date', 'due_date', 'assignee_id', 'priority', 'story_points'] as const

const EMPTY_VALUES: CreateTaskValues = {
  title: '',
  description: '',
  start_date: '',
  due_date: '',
  assignee_id: null,
  priority: null,
  story_points: null,
}

// US-011 · Mockup: docs/tasarim/04-proje-detay-kanban.png ("Yeni görev")
export function TaskCreateDialog({ projectId, trigger }: { projectId: number; trigger: ReactNode }) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const form = useForm<CreateTaskValues>({
    resolver: zodResolver(createTaskSchema),
    defaultValues: EMPTY_VALUES,
  })
  const { errors } = form.formState
  const startDate = useWatch({ control: form.control, name: 'start_date' })

  const create = useMutation({
    mutationFn: (values: CreateTaskValues) =>
      tasksApi.create(projectId, {
        title: values.title,
        description: values.description || null,
        start_date: values.start_date || null,
        due_date: values.due_date || null,
        assignee_id: values.assignee_id,
        ...(values.priority !== null ? { priority: values.priority } : {}),
        ...(values.story_points !== null ? { story_points: values.story_points } : {}),
      }),
    onSuccess: (task) => {
      queryClient.setQueryData(taskKeys.detail(task.id), task)
      // Yeni görev Kanban'ın To Do sütununda, proje ilerlemesi de güncel görünsün
      void queryClient.invalidateQueries({ queryKey: taskKeys.board(projectId) })
      void queryClient.invalidateQueries({ queryKey: ['projects'] })
      toast.success(`"${task.title}" görevi oluşturuldu.`)
      setOpen(false)
    },
    onError: (error) => {
      if (error instanceof ApiError && error.code === 'INVALID_DATE_RANGE') {
        form.setError('due_date', { message: DATE_RANGE_MESSAGE }, { shouldFocus: true })
        return
      }
      if (error instanceof ApiError && error.code === 'ASSIGNEE_NOT_MEMBER') {
        form.setError('assignee_id', { message: error.message })
        return
      }
      setFormError(applyApiErrors(error, form.setError, FIELDS))
    },
  })

  const handleOpenChange = (next: boolean) => {
    if (create.isPending) return
    setOpen(next)
    // Pencere her açılışta boş formla başlasın
    if (next) {
      form.reset(EMPTY_VALUES)
      setFormError(null)
    }
  }

  const onSubmit = form.handleSubmit((values) => {
    setFormError(null)
    create.mutate(values)
  })

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="max-h-[90dvh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Yeni görev</DialogTitle>
          <DialogDescription>Görev Kanban panosunun To Do sütununa eklenir.</DialogDescription>
        </DialogHeader>

        <form id="task-create-form" onSubmit={onSubmit} noValidate className="grid gap-5">
          <FormField id="task-title" label="Başlık" error={errors.title?.message}>
            <Input id="task-title" placeholder="Giriş ekranı" aria-invalid={!!errors.title} {...form.register('title')} />
          </FormField>

          <FormField id="task-description" label="Açıklama" error={errors.description?.message} hint="İsteğe bağlı">
            <Textarea
              id="task-description"
              rows={3}
              placeholder="Görevin ayrıntıları…"
              aria-invalid={!!errors.description}
              {...form.register('description')}
            />
          </FormField>

          <div className="grid gap-5 sm:grid-cols-2">
            <FormField id="task-start" label="Başlangıç tarihi" error={errors.start_date?.message}>
              <Input id="task-start" type="date" aria-invalid={!!errors.start_date} {...form.register('start_date')} />
            </FormField>

            {/* Takvimde başlangıçtan önceki günler seçilemez */}
            <FormField id="task-due" label="Teslim tarihi" error={errors.due_date?.message}>
              <Input
                id="task-due"
                type="date"
                min={startDate || undefined}
                aria-invalid={!!errors.due_date}
                {...form.register('due_date')}
              />
            </FormField>
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            <FormField id="create-task-priority" label="Öncelik" error={errors.priority?.message}>
              <Controller name="priority" control={form.control} render={({ field }) => (
                <select id="create-task-priority" ref={field.ref} onBlur={field.onBlur}
                  value={field.value ?? ''} onChange={(event) => field.onChange(event.target.value || null)}
                  disabled={create.isPending} className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  aria-invalid={!!errors.priority} aria-describedby={errors.priority ? 'create-task-priority-error' : undefined}>
                  <option value="">Belirtilmedi</option>
                  {Object.entries(PRIORITY_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
              )} />
            </FormField>
            <FormField id="create-task-story-points" label="Efor puanı" error={errors.story_points?.message}>
              <Controller name="story_points" control={form.control} render={({ field }) => (
                <select id="create-task-story-points" ref={field.ref} onBlur={field.onBlur}
                  value={field.value ?? ''} onChange={(event) => field.onChange(event.target.value === '' ? null : Number(event.target.value))}
                  disabled={create.isPending} className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  aria-invalid={!!errors.story_points} aria-describedby={errors.story_points ? 'create-task-story-points-error' : undefined}>
                  <option value="">Belirtilmedi</option>
                  {STORY_POINT_OPTIONS.map((value) => <option key={value} value={value}>{value} puan</option>)}
                </select>
              )} />
            </FormField>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="task-assignee">Atanan kişi</Label>
            <Controller
              control={form.control}
              name="assignee_id"
              render={({ field }) => (
                <AssigneeSelect
                  id="task-assignee"
                  projectId={projectId}
                  value={field.value}
                  onChange={field.onChange}
                  invalid={!!errors.assignee_id}
                />
              )}
            />
            {errors.assignee_id && <p className="text-sm text-destructive">{errors.assignee_id.message}</p>}
          </div>

          {formError && (
            <Alert variant="destructive">
              <CircleAlertIcon />
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          )}
        </form>

        <DialogFooter>
          <Button variant="secondary" disabled={create.isPending} onClick={() => handleOpenChange(false)}>
            İptal
          </Button>
          <Button type="submit" form="task-create-form" disabled={create.isPending}>
            {create.isPending && <Loader2Icon className="animate-spin" />}
            Oluştur
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
