import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { FormField } from '@/components/form/FormField'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ApiError } from '@/lib/api'
import { applyApiErrors } from '@/lib/form-errors'
import { projectsApi } from './api'
import type { Project, UpdateProjectInput } from './types'

interface FormValues {
  name: string
  description: string
  start_date: string
  end_date: string
}

interface Props {
  project: Project
  onClose: () => void
}

const fields = [
  'name',
  'description',
  'start_date',
  'end_date',
] as const

export function ProjectEditForm({ project, onClose }: Props) {
  const queryClient = useQueryClient()
  const [formError, setFormError] = useState<string | null>(null)

  const form = useForm<FormValues>({
    defaultValues: {
      name: project.name,
      description: project.description ?? '',
      start_date: project.start_date ?? '',
      end_date: project.end_date ?? '',
    },
  })

  const { errors, isDirty } = form.formState

  const update = useMutation({
    mutationFn: (values: UpdateProjectInput) =>
      projectsApi.update(project.id, values),
    meta: { skipForbiddenToast: true },

    onSuccess: (updatedProject) => {
      queryClient.setQueryData(
        ['projects', 'detail', project.id],
        updatedProject,
      )

      void queryClient.invalidateQueries({
        queryKey: ['projects', 'list'],
      })

      toast.success('Proje bilgileri güncellendi.')
      onClose()
    },

    onError: (error) => {
      if (
        error instanceof ApiError &&
        error.code === 'INVALID_DATE_RANGE'
      ) {
        form.setError(
          'end_date',
          {
            message: 'Bitiş tarihi başlangıç tarihinden önce olamaz.',
          },
          { shouldFocus: true },
        )
        return
      }

      setFormError(
        applyApiErrors(error, form.setError, fields),
      )
    },
  })

  const onSubmit = form.handleSubmit((values) => {
    setFormError(null)

    if (
      values.start_date &&
      values.end_date &&
      values.end_date < values.start_date
    ) {
      form.setError(
        'end_date',
        {
          message: 'Bitiş tarihi başlangıç tarihinden önce olamaz.',
        },
        { shouldFocus: true },
      )
      return
    }

    const changes: UpdateProjectInput = {}
    const name = values.name.trim()

    if (name !== project.name) {
      changes.name = name
    }

    if (values.description !== (project.description ?? '')) {
      changes.description = values.description
    }

    if (values.start_date !== (project.start_date ?? '')) {
      changes.start_date = values.start_date || null
    }

    if (values.end_date !== (project.end_date ?? '')) {
      changes.end_date = values.end_date || null
    }

    if (Object.keys(changes).length === 0) {
      onClose()
      return
    }

    update.mutate(changes)
  })

  return (
    <form onSubmit={onSubmit} noValidate className="grid gap-5">
      <div>
        <h2 className="text-xl font-semibold">
          Projeyi düzenle
        </h2>
        <p className="text-sm text-muted-foreground">
          Proje bilgilerini ve tarihlerini güncelle.
        </p>
      </div>

      <fieldset disabled={update.isPending} className="grid gap-5">
        <FormField
          id="project-name"
          label="Proje adı"
          error={errors.name?.message}
        >
          <Input
            id="project-name"
            aria-invalid={!!errors.name}
            aria-describedby={
              errors.name ? 'project-name-error' : undefined
            }
            {...form.register('name', {
              validate: (value) => {
                const name = value.trim()

                if (!name) {
                  return 'Proje adı zorunludur.'
                }

                if (name.length < 2) {
                  return 'Proje adı en az 2 karakter olmalıdır.'
                }

                if (name.length > 100) {
                  return 'Proje adı en fazla 100 karakter olabilir.'
                }

                return true
              },
            })}
          />
        </FormField>

        <FormField
          id="project-description"
          label="Açıklama"
          error={errors.description?.message}
        >
          <textarea
            id="project-description"
            rows={4}
            className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-ring"
            aria-invalid={!!errors.description}
            aria-describedby={
              errors.description
                ? 'project-description-error'
                : undefined
            }
            {...form.register('description', {
              maxLength: {
                value: 2000,
                message: 'Açıklama en fazla 2000 karakter olabilir.',
              },
            })}
          />
        </FormField>

        <div className="grid gap-5 sm:grid-cols-2">
          <FormField
            id="project-start"
            label="Başlangıç tarihi"
            error={errors.start_date?.message}
          >
            <Input
              id="project-start"
              type="date"
              aria-invalid={!!errors.start_date}
              aria-describedby={
                errors.start_date
                  ? 'project-start-error'
                  : undefined
              }
              {...form.register('start_date')}
            />
          </FormField>

          <FormField
            id="project-end"
            label="Bitiş tarihi"
            error={errors.end_date?.message}
          >
            <Input
              id="project-end"
              type="date"
              aria-invalid={!!errors.end_date}
              aria-describedby={
                errors.end_date
                  ? 'project-end-error'
                  : undefined
              }
              {...form.register('end_date')}
            />
          </FormField>
        </div>
      </fieldset>

      {formError && (
        <Alert variant="destructive" role="alert">
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      )}

      <div className="flex flex-wrap justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          disabled={update.isPending}
          onClick={onClose}
        >
          Vazgeç
        </Button>

        <Button
          type="submit"
          disabled={update.isPending || !isDirty}
        >
          {update.isPending
            ? 'Kaydediliyor…'
            : 'Değişiklikleri kaydet'}
        </Button>
      </div>
    </form>
  )
}