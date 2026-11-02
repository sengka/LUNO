import { lazy, Suspense, useState } from 'react'
import { Link, useParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { CalendarIcon, ChartGanttIcon, KanbanIcon, PlusIcon, SettingsIcon } from 'lucide-react'
import { AccessDenied } from '@/components/AccessDenied'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/auth-context'
import { KanbanBoard } from '@/features/tasks/KanbanBoard'
import { TaskCreateDialog } from '@/features/tasks/TaskCreateDialog'
import { ApiError } from '@/lib/api'
import { projectsApi } from './api'
import { ProjectEditForm } from './ProjectEditForm'
import { ProjectDeleteButton } from './ProjectDeleteButton'
import { ProjectMembers } from './ProjectMembers'
import { ProjectInvitePanel } from './ProjectInvitePanel'

const ProjectCalendar = lazy(() => import('./ProjectCalendar'))
const ProjectGantt = lazy(() => import('./ProjectGantt'))

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
  const { projectId, view } = useParams()
  const activeView = view === 'takvim' || view === 'gantt' ? view : 'kanban'
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

    // US-005: Üyesi olunmayan proje (403 PROJECT_ACCESS_DENIED)
    if (status === 403) {
      return (
        <AccessDenied
          title="Bu projeye erişimin yok"
          description="Bu projenin üyesi değilsin. Projeye eklenmek için proje yöneticine başvurabilirsin."
          backTo="/projeler"
          backLabel="Projelerime dön"
        />
      )
    }

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

      <section aria-labelledby="project-board-title" className="grid gap-5">
        <div className="flex flex-wrap items-end justify-between gap-4 border-b">
          <h2 id="project-board-title" className="sr-only">Proje görünümleri</h2>
          <nav aria-label="Proje görünümleri" className="flex flex-wrap gap-4">
            {([
              ['kanban', 'Kanban', KanbanIcon, `/projeler/${project.id}`],
              ['takvim', 'Takvim', CalendarIcon, `/projeler/${project.id}/takvim`],
              ['gantt', 'Gantt', ChartGanttIcon, `/projeler/${project.id}/gantt`],
            ] as const).map(([value, label, Icon, to]) => <Link key={value} to={to} aria-current={activeView === value ? 'page' : undefined} className={`flex items-center gap-2 border-b-2 px-1 pb-3 font-semibold ${activeView === value ? 'border-primary text-brand' : 'border-transparent text-muted-foreground hover:text-brand'}`}><Icon className="size-4" />{label}</Link>)}
          </nav>
          {isAdmin && (
            <div className="pb-3">
              <TaskCreateDialog
                projectId={project.id}
                trigger={
                  <Button>
                    <PlusIcon />
                    Yeni görev
                  </Button>
                }
              />
            </div>
          )}
        </div>
        <Suspense fallback={<p role="status">Görünüm yükleniyor…</p>}>
          {activeView === 'takvim' ? <ProjectCalendar projectId={project.id} /> : activeView === 'gantt' ? <ProjectGantt projectId={project.id} /> : <KanbanBoard projectId={project.id} />}
        </Suspense>
      </section>

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

      <ProjectMembers projectId={project.id} />
            {isAdmin && <ProjectInvitePanel projectId={project.id} />}
    </div>
  )
}
export function ProjectDetailPage() {
  const { projectId } = useParams()

  return <ProjectDetailContent key={projectId} />
}
