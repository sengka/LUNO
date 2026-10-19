import { useState } from 'react'
import { Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { CalendarIcon, FolderOpenIcon, Loader2Icon, PlusIcon, UsersIcon } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/auth-context'
import { ApiError } from '@/lib/api'
import { projectsApi } from './api'
import { ProjectCreateDialog } from './ProjectCreateDialog'
import type { Project } from './types'

const dateFormatter = new Intl.DateTimeFormat('tr-TR', { day: '2-digit', month: '2-digit', year: 'numeric' })

function formatDate(value: string | null) {
  return value ? dateFormatter.format(new Date(`${value}T00:00:00`)) : '—'
}

// US-007 · Mockup: docs/tasarim/03-proje-listesi.png
export function ProjectsPage() {
  const { isAdmin } = useAuth()
  const [page, setPage] = useState(1)

  const projectsQuery = useQuery({
    queryKey: ['projects', 'list', page],
    queryFn: () => projectsApi.list(page),
    retry: false,
  })

  // Proje oluşturma yalnızca yöneticiye görünür (US-005, FR-012)
  const newProjectButton = isAdmin && (
    <ProjectCreateDialog
      trigger={
        <Button>
          <PlusIcon />
          Yeni proje
        </Button>
      }
    />
  )

  return (
    <div className="grid gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="grid gap-1">
          <h1 className="text-2xl font-semibold text-brand">Projeler</h1>
          <p className="text-sm text-muted-foreground">Üyesi olduğun projeleri görüntüle.</p>
        </div>
        {newProjectButton}
      </header>

      {projectsQuery.isPending ? (
        <div role="status" className="flex justify-center py-16">
          <Loader2Icon className="size-6 animate-spin text-primary" />
          <span className="sr-only">Projeler yükleniyor…</span>
        </div>
      ) : projectsQuery.isError ? (
        <div className="grid gap-3">
          <Alert variant="destructive" role="alert">
            <AlertDescription>
              {projectsQuery.error instanceof ApiError ? projectsQuery.error.message : 'Projeler alınamadı.'}
            </AlertDescription>
          </Alert>
          <Button
            variant="outline"
            className="justify-self-start"
            disabled={projectsQuery.isFetching}
            onClick={() => void projectsQuery.refetch()}
          >
            Tekrar dene
          </Button>
        </div>
      ) : projectsQuery.data.total === 0 ? (
        <div className="grid justify-items-center gap-3 rounded-xl border border-dashed bg-card px-6 py-16 text-center">
          <span className="flex size-12 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
            <FolderOpenIcon className="size-6" />
          </span>
          <h2 className="font-semibold">Henüz bir projen yok</h2>
          <p className="max-w-sm text-sm text-muted-foreground">
            {isAdmin
              ? 'İlk projeni oluştur, ekibini ekle ve görevleri planlamaya başla.'
              : 'Bir yönetici seni bir projeye eklediğinde burada görünecek.'}
          </p>
          {newProjectButton}
        </div>
      ) : (
        <>
          {projectsQuery.data.items.length === 0 ? (
            <p className="rounded-xl border bg-card p-6 text-muted-foreground">Bu sayfada gösterilecek proje yok.</p>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {projectsQuery.data.items.map((project) => (
                <ProjectCard key={project.id} project={project} />
              ))}
            </div>
          )}

          {projectsQuery.data.total > projectsQuery.data.limit && (
            <nav aria-label="Proje listesi sayfaları" className="flex flex-wrap items-center justify-between gap-3">
              <Button variant="outline" disabled={page === 1} onClick={() => setPage((current) => current - 1)}>
                Önceki
              </Button>
              <span className="text-sm text-muted-foreground">
                Sayfa {page} · Toplam {projectsQuery.data.total} proje
              </span>
              <Button
                variant="outline"
                disabled={page * projectsQuery.data.limit >= projectsQuery.data.total}
                onClick={() => setPage((current) => current + 1)}
              >
                Sonraki
              </Button>
            </nav>
          )}
        </>
      )}
    </div>
  )
}

function ProjectCard({ project }: { project: Project }) {
  const progress = Math.min(100, Math.max(0, project.progress_percent || 0))
  const progressLabel = progress.toLocaleString('tr-TR', { maximumFractionDigits: 1 })

  return (
    <Link
      to={`/projeler/${project.id}`}
      className="grid content-start gap-4 rounded-xl border bg-card p-5 transition-colors hover:border-primary focus-visible:outline-2 focus-visible:outline-ring"
    >
      <div className="grid gap-1.5">
        <h2 className="break-words text-lg font-semibold">{project.name}</h2>
        <p className="line-clamp-2 break-words text-sm text-muted-foreground">
          {project.description || 'Açıklama eklenmemiş.'}
        </p>
      </div>

      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        <CalendarIcon className="size-4 text-primary" />
        {formatDate(project.start_date)} – {formatDate(project.end_date)}
      </p>

      <div className="grid gap-2">
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">İlerleme</span>
          <span className="font-medium text-brand">%{progressLabel}</span>
        </div>
        <div
          role="progressbar"
          aria-label={`${project.name} ilerlemesi`}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progress}
          className="h-2 overflow-hidden rounded-full bg-secondary"
        >
          <div className="h-full rounded-full bg-primary" style={{ width: `${progress}%` }} />
        </div>
      </div>

      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        <UsersIcon className="size-4" />
        {project.member_count} üye
      </p>
    </Link>
  )
}
