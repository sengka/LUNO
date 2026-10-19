import { useState, type ReactNode } from 'react'
import { useForm, useWatch } from 'react-hook-form'
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
import { Textarea } from '@/components/ui/textarea'
import { FormField } from '@/components/form/FormField'
import { ApiError } from '@/lib/api'
import { applyApiErrors } from '@/lib/form-errors'
import { projectsApi } from './api'

const DATE_RANGE_MESSAGE = 'Bitiş tarihi başlangıç tarihinden önce olamaz.'

// Kurallar sözleşme 5.2 ile aynı (FR-015, FR-016)
const createProjectSchema = z
  .object({
    name: z
      .string()
      .trim()
      .min(2, { error: 'Proje adı en az 2 karakter olmalıdır.' })
      .max(100, { error: 'Proje adı en fazla 100 karakter olabilir.' }),
    description: z.string().trim().max(2000, { error: 'Açıklama en fazla 2000 karakter olabilir.' }),
    start_date: z.string().min(1, { error: 'Başlangıç tarihi zorunludur.' }),
    end_date: z.string().min(1, { error: 'Bitiş tarihi zorunludur.' }),
  })
  // YYYY-MM-DD biçimindeki tarihler metin olarak da doğru sıralanır
  .refine((values) => !values.start_date || !values.end_date || values.end_date >= values.start_date, {
    path: ['end_date'],
    error: DATE_RANGE_MESSAGE,
  })

type CreateProjectValues = z.infer<typeof createProjectSchema>

const FIELDS = ['name', 'description', 'start_date', 'end_date'] as const

const EMPTY_VALUES: CreateProjectValues = { name: '', description: '', start_date: '', end_date: '' }

// Mockup: docs/tasarim/03-proje-listesi.png ("Yeni Proje" penceresi)
export function ProjectCreateDialog({ trigger }: { trigger: ReactNode }) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const form = useForm<CreateProjectValues>({
    resolver: zodResolver(createProjectSchema),
    defaultValues: EMPTY_VALUES,
  })
  const { errors } = form.formState
  const startDate = useWatch({ control: form.control, name: 'start_date' })

  const create = useMutation({
    mutationFn: projectsApi.create,
    onSuccess: (project) => {
      void queryClient.invalidateQueries({ queryKey: ['projects', 'list'] })
      toast.success(`"${project.name}" projesi oluşturuldu.`)
      setOpen(false)
    },
    onError: (error) => {
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
    // Pencere her açılışta boş formla başlasın
    if (next) {
      form.reset(EMPTY_VALUES)
      setFormError(null)
    }
  }

  const onSubmit = form.handleSubmit((values) => {
    setFormError(null)
    create.mutate({ ...values, description: values.description || null })
  })

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Yeni Proje</DialogTitle>
          <DialogDescription>Projenin adını ve tarih aralığını gir. Oluşturan kişi olarak projeye otomatik üye olursun.</DialogDescription>
        </DialogHeader>

        <form id="project-create-form" onSubmit={onSubmit} noValidate className="grid gap-5">
          <FormField id="project-name" label="Proje adı" error={errors.name?.message}>
            <Input
              id="project-name"
              placeholder="Mobil Uygulama v2"
              aria-invalid={!!errors.name}
              {...form.register('name')}
            />
          </FormField>

          <FormField id="project-description" label="Açıklama" error={errors.description?.message} hint="İsteğe bağlı">
            <Textarea
              id="project-description"
              rows={3}
              placeholder="Kısa bir açıklama gir…"
              aria-invalid={!!errors.description}
              {...form.register('description')}
            />
          </FormField>

          <div className="grid gap-5 sm:grid-cols-2">
            <FormField id="project-start" label="Başlangıç tarihi" error={errors.start_date?.message}>
              <Input id="project-start" type="date" aria-invalid={!!errors.start_date} {...form.register('start_date')} />
            </FormField>

            {/* Takvimde başlangıçtan önceki günler seçilemez */}
            <FormField id="project-end" label="Bitiş tarihi" error={errors.end_date?.message}>
              <Input
                id="project-end"
                type="date"
                min={startDate || undefined}
                aria-invalid={!!errors.end_date}
                {...form.register('end_date')}
              />
            </FormField>
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
          <Button type="submit" form="project-create-form" disabled={create.isPending}>
            {create.isPending && <Loader2Icon className="animate-spin" />}
            Kaydet
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
