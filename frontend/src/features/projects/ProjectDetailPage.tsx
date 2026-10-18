import { useState } from 'react'
import { useParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { SettingsIcon } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/auth-context'
import { ApiError } from '@/lib/api'
import { projectsApi } from './api'
import { ProjectEditForm } from './ProjectEditForm'
import { ProjectDeleteButton } from './ProjectDeleteButton'

function formatDate(value: string | null) {
  if (!value) return 'Belirtilmedi'

  const date = new Date(`${value}T00:00:00`)
  if (Number.isNaN(date.getTime())) return 'Geçersiz tarih'

  return new Intl.DateTimeFormat('tr-TR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(date)
}

function ProjectDetailContent() {
  const { projectId } = useParams()
  const id = Number(projectId)
  const validId = Number.isSafeInteger(id) && id > 0
  const { isAdmin } = useAuth()
  const [editing, setEditing] = useState(false)

  const projectQuery = useQuery({
    queryKey: ['projects', 'detail', id],
    queryFn: () => projectsApi.getDetail(id),
    enabled: validId,
    retry: false,
  })

  if (!validId) {
    return (
      <Alert variant="destructive" role="alert">
        <AlertDescription>Geçersiz proje numarası.</AlertDescription>
      </Alert>
    )
  }

  if (projectQuery.isPending) {
    return (
      <p role="status" className="text-muted-foreground">
        Proje bilgileri yükleniyor…
      </p>
    )
  }

  if (projectQuery.isError) {
    const error = projectQuery.error
    const status = error instanceof ApiError ? error.status : null

    const message =
      status === 403
        ? 'Bu projeyi görüntüleme yetkin yok.'
        : status === 404
          ? 'Proje bulunamadı.'
          : error instanceof ApiError
            ? error.message
            : 'Proje bilgileri alınamadı.'

    return (
      <div className="grid gap-4">
        <Alert variant="destructive" role="alert">
          <AlertDescription>{message}</AlertDescription>
        </Alert>

        {status !== 403 && status !== 404 && (
          <Button
            variant="outline"
            className="justify-self-start"
            disabled={projectQuery.isFetching}
            onClick={() => void projectQuery.refetch()}
          >
            Tekrar dene
          </Button>
        )}
      </div>
    )
  }

  const project = projectQuery.data
  const progress = Math.min(
    100,
    Math.max(0, project.progress_percent || 0),
  )

  return (
    <div className="grid gap-6">
      <header className="grid gap-5 rounded-xl border bg-card p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="mb-1 text-sm text-muted-foreground">
              Proje detayı
            </p>
            <h1 className="break-words text-2xl font-semibold">
              {project.name}
            </h1>
          </div>

          {isAdmin && (
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                onClick={() => setEditing((current) => !current)}
                aria-expanded={editing}
                aria-controls="project-edit-panel"
              >
                <SettingsIcon className="size-4" />
                {editing ? 'Düzenlemeyi kapat' : 'Projeyi düzenle'}
              </Button>

              <ProjectDeleteButton project={project} />
            </div>
          )}
        </div>

        <div className="grid gap-2">
          <div className="flex justify-between gap-4 text-sm">
            <span className="text-muted-foreground">
              Genel ilerleme
            </span>
            <span className="font-medium">
              %{progress.toLocaleString('tr-TR', {
                maximumFractionDigits: 1,
              })}
            </span>
          </div>

          <div
            role="progressbar"
            aria-label="Proje ilerlemesi"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progress}
            className="h-2 overflow-hidden rounded-full bg-secondary"
          >
            <div
              className="h-full rounded-full bg-primary"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </header>

      {isAdmin && editing && (
        <section
          id="project-edit-panel"
          aria-label="Proje düzenleme"
          className="rounded-xl border bg-card p-5 sm:p-6"
        >
          <ProjectEditForm
            key={project.id}
            project={project}
            onClose={() => setEditing(false)}
          />
        </section>
      )}

      <section
        aria-labelledby="project-info-title"
        className="grid gap-5 rounded-xl border bg-card p-5 sm:p-6"
      >
        <h2 id="project-info-title" className="text-lg font-semibold">
          Proje bilgileri
        </h2>

        <p className="whitespace-pre-wrap break-words text-sm text-muted-foreground">
          {project.description || 'Bu proje için açıklama eklenmemiş.'}
        </p>

        <dl className="grid gap-5 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-muted-foreground">Başlangıç tarihi</dt>
            <dd className="mt-1 font-medium">
              {formatDate(project.start_date)}
            </dd>
          </div>

          <div>
            <dt className="text-muted-foreground">Bitiş tarihi</dt>
            <dd className="mt-1 font-medium">
              {formatDate(project.end_date)}
            </dd>
          </div>

          <div>
            <dt className="text-muted-foreground">Ekip üyesi sayısı</dt>
            <dd className="mt-1 font-medium">{project.member_count}</dd>
          </div>

          <div>
            <dt className="text-muted-foreground">Oluşturan</dt>
            <dd className="mt-1 font-medium">
              {project.created_by?.full_name ?? 'Belirtilmedi'}
            </dd>
          </div>
        </dl>
      </section>
    </div>
  )
}
export function ProjectDetailPage() {
  const { projectId } = useParams()

  return <ProjectDetailContent key={projectId} />
}