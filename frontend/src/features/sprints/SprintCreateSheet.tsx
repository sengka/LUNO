import { useState, type ReactNode } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { z } from 'zod'
import { CircleAlertIcon, Loader2Icon } from 'lucide-react'
import { toast } from 'sonner'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { Textarea } from '@/components/ui/textarea'
import { FormField } from '@/components/form/FormField'
import { ApiError } from '@/lib/api'
import { applyApiErrors } from '@/lib/form-errors'
import { sprintKeys, sprintsApi } from './api'
import type { Sprint } from './types'

const DATE_RANGE_MESSAGE = 'Bitiş tarihi başlangıç tarihinden önce olamaz.'

// Kurallar sözleşme 11.1 ve backend şemasıyla aynı (FR-066)
const sprintSchema = z
  .object({
    name: z
      .string()
      .trim()
      .min(1, { error: 'Sprint adı zorunludur.' })
      .max(100, { error: 'Sprint adı en fazla 100 karakter olabilir.' }),
    goal: z.string().trim().max(2000, { error: 'Hedef en fazla 2000 karakter olabilir.' }),
    start_date: z.string().min(1, { error: 'Başlangıç tarihi zorunludur.' }),
    end_date: z.string().min(1, { error: 'Bitiş tarihi zorunludur.' }),
    // Boş bırakılırsa kapasite sınırı yok (sözleşme 11.2)
    capacity_points: z
      .string()
      .trim()
      .refine((value) => value === '' || (/^\d+$/.test(value) && Number(value) > 0), {
        error: 'Kapasite pozitif bir tam sayı olmalıdır.',
      }),
  })
  .refine((values) => !values.start_date || !values.end_date || values.end_date >= values.start_date, {
    path: ['end_date'],
    error: DATE_RANGE_MESSAGE,
  })

type SprintFormValues = z.infer<typeof sprintSchema>

const FIELDS = ['name', 'goal', 'start_date', 'end_date', 'capacity_points'] as const

const EMPTY: SprintFormValues = { name: '', goal: '', start_date: '', end_date: '', capacity_points: '' }

interface SprintCreateSheetProps {
  projectId: number
  trigger: ReactNode
  onCreated: (sprint: Sprint) => void
}

// US-040 · Mockup: docs/tasarim/mockup/sprint-planlama.png ("Sprint oluştur" paneli)
export function SprintCreateSheet({ projectId, trigger, onCreated }: SprintCreateSheetProps) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const form = useForm<SprintFormValues>({ resolver: zodResolver(sprintSchema), defaultValues: EMPTY })
  const { errors } = form.formState
  const startDate = useWatch({ control: form.control, name: 'start_date' })

  const create = useMutation({
    mutationFn: (values: SprintFormValues) =>
      sprintsApi.create(projectId, {
        name: values.name,
        goal: values.goal || null,
        start_date: values.start_date,
        end_date: values.end_date,
        capacity_points: values.capacity_points === '' ? null : Number(values.capacity_points),
      }),
    onSuccess: (sprint) => {
      void queryClient.invalidateQueries({ queryKey: sprintKeys.list(projectId) })
      toast.success(`"${sprint.name}" oluşturuldu.`)
      setOpen(false)
      onCreated(sprint)
    },
    onError: (error) => {
      if (error instanceof ApiError && error.code === 'SPRINT_OVERLAP') {
        // Mockup'taki gibi iki tarih alanı da işaretlenir
        form.setError('start_date', { message: ' ' })
        form.setError('end_date', { message: error.message }, { shouldFocus: true })
        return
      }
      if (error instanceof ApiError && error.code === 'INVALID_DATE_RANGE') {
        form.setError('end_date', { message: DATE_RANGE_MESSAGE }, { shouldFocus: true })
        return
      }
      setFormError(applyApiErrors(error, form.setError, FIELDS))
    },
  })

  const handleOpenChange = (next: boolean) => {
    if (create.isPending) return
    setOpen(next)
    if (next) {
      form.reset(EMPTY)
      setFormError(null)
    }
  }

  const onSubmit = form.handleSubmit((values) => {
    setFormError(null)
    create.mutate(values)
  })

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetTrigger asChild>{trigger}</SheetTrigger>
      <SheetContent side="right" className="w-full gap-0 sm:max-w-md">
        <SheetHeader className="border-b">
          <SheetTitle className="text-brand">Sprint oluştur</SheetTitle>
          <SheetDescription>Sprintin hedefini, tarihlerini ve ekip kapasitesini belirle.</SheetDescription>
        </SheetHeader>

        <form id="sprint-create-form" onSubmit={onSubmit} noValidate className="grid gap-5 overflow-y-auto p-4">
          <FormField id="sprint-name" label="Ad" error={errors.name?.message}>
            <Input id="sprint-name" placeholder="Sprint 4" aria-invalid={!!errors.name} {...form.register('name')} />
          </FormField>

          <FormField id="sprint-goal" label="Hedef" error={errors.goal?.message} hint="İsteğe bağlı">
            <Textarea
              id="sprint-goal"
              rows={3}
              placeholder="Profil ve hesap ayarları tamamlansın"
              aria-invalid={!!errors.goal}
              {...form.register('goal')}
            />
          </FormField>

          <FormField id="sprint-start" label="Başlangıç" error={errors.start_date?.message?.trim() || undefined}>
            <Input id="sprint-start" type="date" aria-invalid={!!errors.start_date} {...form.register('start_date')} />
          </FormField>

          <FormField id="sprint-end" label="Bitiş" error={errors.end_date?.message}>
            <Input
              id="sprint-end"
              type="date"
              min={startDate || undefined}
              aria-invalid={!!errors.end_date}
              {...form.register('end_date')}
            />
          </FormField>

          <FormField
            id="sprint-capacity"
            label="Kapasite (puan)"
            error={errors.capacity_points?.message}
            hint="Boş bırakılırsa kapasite sınırı uygulanmaz"
          >
            <Input
              id="sprint-capacity"
              type="number"
              inputMode="numeric"
              min={1}
              placeholder="40"
              aria-invalid={!!errors.capacity_points}
              {...form.register('capacity_points')}
            />
          </FormField>

          {formError && (
            <Alert variant="destructive">
              <CircleAlertIcon />
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          )}

          <div className="flex gap-2">
            <Button type="button" variant="secondary" disabled={create.isPending} onClick={() => handleOpenChange(false)}>
              Vazgeç
            </Button>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending && <Loader2Icon className="animate-spin" />}
              Kaydet
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  )
}
