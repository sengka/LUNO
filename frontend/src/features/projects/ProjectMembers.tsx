import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { FormField } from '@/components/form/FormField'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAuth } from '@/features/auth/auth-context'
import { ApiError } from '@/lib/api'
import { applyApiErrors } from '@/lib/form-errors'
import { ROLE_LABELS } from '@/types/api'
import { membersApi } from './members-api'
import type { AddMemberInput, ProjectMember } from './member-types'

interface Props {
  projectId: number
}

interface FormValues {
  email: string
  technical_role: string
}

export function ProjectMembers({ projectId }: Props) {
  const { user, isAdmin } = useAuth()
  const queryClient = useQueryClient()
  const [formError, setFormError] = useState<string | null>(null)
  const [removeError, setRemoveError] = useState<string | null>(null)
  const [memberToRemove, setMemberToRemove] = useState<ProjectMember | null>(null)

  const form = useForm<FormValues>({
    defaultValues: {
      email: '',
      technical_role: '',
    },
  })

  const membersQuery = useQuery({
    queryKey: ['projects', 'members', projectId],
    queryFn: () => membersApi.list(projectId),
    retry: false,
  })

  const refreshProject = () => {
    void queryClient.invalidateQueries({
      queryKey: ['projects'],
    })
  }

  const addMember = useMutation({
    mutationFn: (values: AddMemberInput) =>
      membersApi.add(projectId, values),
    meta: { skipForbiddenToast: true },
    onSuccess: () => {
      form.reset()
      setFormError(null)
      refreshProject()
      toast.success('Üye projeye eklendi.')
    },
    onError: (error) => {
      if (
        error instanceof ApiError &&
        (error.code === 'USER_NOT_FOUND' ||
          error.code === 'ALREADY_MEMBER')
      ) {
        form.setError(
          'email',
          { message: error.message },
          { shouldFocus: true },
        )
        return
      }

      setFormError(
        applyApiErrors(error, form.setError, [
          'email',
          'technical_role',
        ]),
      )
    },
  })

  const removeMember = useMutation({
    mutationFn: (userId: number) =>
      membersApi.remove(projectId, userId),
    meta: { skipForbiddenToast: true },
    onSuccess: () => {
      setRemoveError(null)
      setMemberToRemove(null)
      refreshProject()
      toast.success('Üye projeden çıkarıldı.')
    },
    onError: (error) => {
      setMemberToRemove(null)
      setRemoveError(
        error instanceof ApiError
          ? error.message
          : 'Üye çıkarılamadı. Lütfen tekrar dene.',
      )
    },
  })

  const onSubmit = form.handleSubmit((values) => {
    setFormError(null)

    const technicalRole = values.technical_role.trim()

    addMember.mutate({
      email: values.email.trim(),
      ...(technicalRole ? { technical_role: technicalRole } : {}),
    })
  })

  const confirmRemove = (member: ProjectMember) => {
    if (!isAdmin || removeMember.isPending) return
    setRemoveError(null)
    setMemberToRemove(member)
  }

  const { errors } = form.formState

  return (
    <section
      aria-labelledby="project-members-title"
      className="grid gap-6 rounded-xl border bg-card p-5 sm:p-6"
    >
      <div>
        <h2
          id="project-members-title"
          className="text-lg font-semibold"
        >
          Proje üyeleri
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Projede yer alan ekip üyeleri ve rolleri.
        </p>
      </div>

      {membersQuery.isPending && (
        <p role="status" className="text-sm text-muted-foreground">
          Üyeler yükleniyor…
        </p>
      )}

      {membersQuery.isError && (
        <div className="grid gap-3">
          <Alert variant="destructive" role="alert">
            <AlertDescription>
              {membersQuery.error instanceof ApiError
                ? membersQuery.error.message
                : 'Üye listesi alınamadı.'}
            </AlertDescription>
          </Alert>
          <Button
            type="button"
            variant="outline"
            className="justify-self-start"
            disabled={membersQuery.isFetching}
            onClick={() => void membersQuery.refetch()}
          >
            Tekrar dene
          </Button>
        </div>
      )}

      {membersQuery.isSuccess && (
        membersQuery.data.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Bu projede gösterilecek üye yok.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">
                Proje üyeleri ve rolleri
              </caption>
              <thead>
                <tr className="border-b">
                  <th scope="col" className="px-3 py-3">Ad soyad</th>
                  <th scope="col" className="px-3 py-3">E-posta</th>
                  <th scope="col" className="px-3 py-3">Sistem rolü</th>
                  <th scope="col" className="px-3 py-3">Teknik rol</th>
                  {isAdmin && (
                    <th scope="col" className="px-3 py-3">İşlem</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {membersQuery.data.map((member) => (
                  <tr key={member.user.id} className="border-b last:border-0">
                    <td className="px-3 py-3 font-medium">
                      {member.user.full_name}
                      {member.user.id === user?.id && (
                        <span className="ml-2 text-xs text-muted-foreground">
                          (Sen)
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-3">{member.email}</td>
                    <td className="px-3 py-3">
                      {ROLE_LABELS[member.system_role]}
                    </td>
                    <td className="px-3 py-3">
                      {member.technical_role || 'Belirtilmedi'}
                    </td>
                    {isAdmin && (
                      <td className="px-3 py-3">
                        {member.user.id === user?.id ? (
                          <span className="text-xs text-muted-foreground">
                            Kendini çıkaramazsın
                          </span>
                        ) : (
                          <Button
                            type="button"
                            variant="destructive"
                            disabled={removeMember.isPending}
                            aria-label={`${member.user.full_name} adlı üyeyi projeden çıkar`}
                            onClick={() => confirmRemove(member)}
                          >
                            {removeMember.isPending &&
                            removeMember.variables === member.user.id
                              ? 'Çıkarılıyor…'
                              : 'Çıkar'}
                          </Button>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}

      <ConfirmDialog
        open={memberToRemove !== null}
        onOpenChange={(open) => {
          if (!open) setMemberToRemove(null)
        }}
        title="Üyeyi projeden çıkar"
        description={
          memberToRemove && (
            <>
              <strong>{memberToRemove.user.full_name}</strong> adlı üyeyi projeden çıkarmak istiyor musun? Bu
              projede kendisine atanmış görevler atanmamış duruma geçecek.
            </>
          )
        }
        confirmLabel="Projeden çıkar"
        pending={removeMember.isPending}
        onConfirm={() => memberToRemove && removeMember.mutate(memberToRemove.user.id)}
      />

      {removeError && (
        <Alert variant="destructive" role="alert">
          <AlertDescription>{removeError}</AlertDescription>
        </Alert>
      )}

      {isAdmin && (
        <form
          onSubmit={onSubmit}
          noValidate
          className="grid gap-4 border-t pt-5"
        >
          <h3 className="font-medium">E-posta ile üye ekle</h3>

          <fieldset
            disabled={addMember.isPending}
            className="grid gap-4 sm:grid-cols-2"
          >
            <FormField
              id="member-email"
              label="E-posta"
              error={errors.email?.message}
            >
              <Input
                id="member-email"
                type="email"
                autoComplete="email"
                placeholder="ornek@mail.com"
                aria-invalid={!!errors.email}
                aria-describedby={
                  errors.email ? 'member-email-error' : undefined
                }
                {...form.register('email', {
                  required: 'E-posta zorunludur.',
                  validate: (value) =>
                    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim()) ||
                    'Geçerli bir e-posta adresi gir.',
                })}
              />
            </FormField>

            <FormField
              id="member-technical-role"
              label="Teknik rol (isteğe bağlı)"
              error={errors.technical_role?.message}
            >
              <Input
                id="member-technical-role"
                placeholder="Örn. Frontend Geliştirici"
                aria-invalid={!!errors.technical_role}
                aria-describedby={
                  errors.technical_role
                    ? 'member-technical-role-error'
                    : undefined
                }
                {...form.register('technical_role', {
                  maxLength: {
                    value: 100,
                    message: 'Teknik rol en fazla 100 karakter olabilir.',
                  },
                })}
              />
            </FormField>
          </fieldset>

          {formError && (
            <Alert variant="destructive" role="alert">
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          )}

          <Button
            type="submit"
            disabled={addMember.isPending}
            className="justify-self-start"
          >
            {addMember.isPending ? 'Ekleniyor…' : 'Üye ekle'}
          </Button>
        </form>
      )}
    </section>
  )
}