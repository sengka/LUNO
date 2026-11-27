import { useState } from 'react'
import { Link } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CalendarIcon, Loader2Icon, PlusIcon, TriangleAlertIcon, XIcon } from 'lucide-react'
import { toast } from 'sonner'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { UserAvatar } from '@/components/UserAvatar'
import { useAuth } from '@/features/auth/auth-context'
import { taskKeys } from '@/features/tasks/api'
import type { Task } from '@/features/tasks/types'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'
import { sprintKeys, sprintsApi } from './api'
import { SprintCreateSheet } from './SprintCreateSheet'
import { PHASE_LABELS, PHASE_STYLES, formatPercent, formatSprintRange, sprintPhase } from './sprint-utils'
import type { Sprint } from './types'

const points = (task: Task) => task.story_points ?? 0

// Varsayılan seçili sprint: aktif olan, yoksa ilk planlanan, yoksa en son sprint
function defaultSprint(sprints: Sprint[]) {
  return (
    sprints.find((s) => s.is_active) ?? sprints.find((s) => sprintPhase(s) === 'planned') ?? sprints[sprints.length - 1]
  )
}

// US-040 · Mockup: docs/tasarim/mockup/sprint-planlama.png
export function SprintPlanning({ projectId }: { projectId: number }) {
  const { isAdmin } = useAuth()
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [targetId, setTargetId] = useState<number | null>(null)
  const [checked, setChecked] = useState<Set<number>>(new Set())

  const sprintsQuery = useQuery({ queryKey: sprintKeys.list(projectId), queryFn: () => sprintsApi.list(projectId) })
  const sprints = sprintsQuery.data ?? []
  const selected = sprints.find((s) => s.id === selectedId) ?? (sprints.length ? defaultSprint(sprints) : undefined)

  const sprintTasksQuery = useQuery({
    queryKey: sprintKeys.tasks(selected?.id ?? 0),
    queryFn: () => sprintsApi.tasksOf(projectId, selected!.id),
    enabled: !!selected,
  })

  const backlogQuery = useQuery({
    queryKey: sprintKeys.backlog(projectId),
    queryFn: () => sprintsApi.openTasks(projectId),
    select: (data) => data.items.filter((task) => task.sprint_id === null),
  })
  const backlog = backlogQuery.data ?? []

  // Görev eklenebilecek sprintler: bitmemiş olanlar
  const openSprints = sprints.filter((s) => sprintPhase(s) !== 'done')
  const target =
    openSprints.find((s) => s.id === targetId) ??
    (selected && sprintPhase(selected) !== 'done' ? selected : openSprints[0])

  const checkedTasks = backlog.filter((task) => checked.has(task.id))
  const checkedPoints = checkedTasks.reduce((sum, task) => sum + points(task), 0)
  const projected = (target?.total_points ?? 0) + checkedPoints
  const overCapacity = target?.capacity_points != null && projected > target.capacity_points

  // Sprint değişince ilerleme kartı, Kanban ve backlog birlikte güncellensin
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: sprintKeys.list(projectId) })
    void queryClient.invalidateQueries({ queryKey: sprintKeys.backlog(projectId) })
    void queryClient.invalidateQueries({ queryKey: ['tasks', 'sprint-tasks'] })
    void queryClient.invalidateQueries({ queryKey: taskKeys.board(projectId) })
  }

  const addTasks = useMutation({
    mutationFn: ({ sprintId, taskIds }: { sprintId: number; taskIds: number[] }) =>
      sprintsApi.addTasks(sprintId, taskIds),
    onSuccess: (sprint, { taskIds }) => {
      setChecked(new Set())
      setSelectedId(sprint.id)
      refresh()
      // Sözleşme 11.3: kapasite aşılsa da görevler eklenir, frontend uyarır
      if (sprint.capacity_warning) {
        toast.warning(`${taskIds.length} görev eklendi, ancak ${sprint.name} kapasitesi aşıldı (${sprint.total_points} / ${sprint.capacity_points} puan).`)
      } else {
        toast.success(`${taskIds.length} görev ${sprint.name} sprintine eklendi.`)
      }
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : 'Görevler sprinte eklenemedi.'),
  })

  const removeTask = useMutation({
    mutationFn: ({ sprintId, taskId }: { sprintId: number; taskId: number }) => sprintsApi.removeTask(sprintId, taskId),
    onSuccess: () => {
      refresh()
      toast.success('Görev sprintten çıkarıldı.')
    },
    onError: (error) => toast.error(error instanceof ApiError ? error.message : 'Görev sprintten çıkarılamadı.'),
  })

  const toggle = (taskId: number) =>
    setChecked((current) => {
      const next = new Set(current)
      if (next.has(taskId)) next.delete(taskId)
      else next.add(taskId)
      return next
    })

  if (sprintsQuery.isPending) {
    return (
      <div role="status" className="flex justify-center py-12">
        <Loader2Icon className="size-6 animate-spin text-primary" />
        <span className="sr-only">Sprintler yükleniyor…</span>
      </div>
    )
  }

  if (sprintsQuery.isError) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          {sprintsQuery.error instanceof ApiError ? sprintsQuery.error.message : 'Sprintler alınamadı.'}
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="grid gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="grid gap-1">
          <h2 className="text-xl font-semibold text-brand">Sprintler</h2>
          <p className="text-sm text-muted-foreground">Hedefleri belirle, ekibinin kapasitesini planla.</p>
        </div>
        {isAdmin && (
          <SprintCreateSheet
            projectId={projectId}
            onCreated={(sprint) => setSelectedId(sprint.id)}
            trigger={
              <Button>
                <PlusIcon />
                Sprint oluştur
              </Button>
            }
          />
        )}
      </header>

      {!selected ? (
        <div className="grid justify-items-center gap-2 rounded-xl border border-dashed bg-card px-6 py-12 text-center">
          <h3 className="font-semibold">Henüz sprint yok</h3>
          <p className="max-w-sm text-sm text-muted-foreground">
            {isAdmin
              ? 'İlk sprinti oluştur, backlog\'daki görevleri sprinte ekleyerek planlamaya başla.'
              : 'Bir yönetici sprint oluşturduğunda burada görünecek.'}
          </p>
        </div>
      ) : (
        <SelectedSprintCard
          sprint={selected}
          tasks={sprintTasksQuery.data?.items}
          loading={sprintTasksQuery.isPending}
          canEdit={isAdmin}
          removingId={removeTask.isPending ? removeTask.variables?.taskId : undefined}
          onRemove={(taskId) => removeTask.mutate({ sprintId: selected.id, taskId })}
        />
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <section aria-labelledby="all-sprints-title" className="grid content-start gap-3">
          <h3 id="all-sprints-title" className="flex items-center justify-between font-semibold text-brand">
            Tüm sprintler
            <span className="rounded-full bg-secondary px-2 text-sm font-medium text-secondary-foreground">
              {sprints.length}
            </span>
          </h3>
          {sprints.map((sprint) => {
            const phase = sprintPhase(sprint)
            return (
              <button
                key={sprint.id}
                type="button"
                onClick={() => setSelectedId(sprint.id)}
                aria-pressed={selected?.id === sprint.id}
                className={cn(
                  'grid gap-2 rounded-xl border bg-card p-4 text-left transition-colors hover:border-primary focus-visible:outline-2 focus-visible:outline-ring',
                  selected?.id === sprint.id && 'border-primary bg-secondary/40',
                )}
              >
                <span className="flex items-center justify-between gap-2">
                  <span className="font-semibold">{sprint.name}</span>
                  <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', PHASE_STYLES[phase])}>
                    {PHASE_LABELS[phase]}
                  </span>
                </span>
                <span className="flex items-center gap-2 text-sm text-muted-foreground">
                  <CalendarIcon className="size-4" />
                  {formatSprintRange(sprint.start_date, sprint.end_date)}
                </span>
                <span className="text-sm text-muted-foreground">
                  {sprint.done_points} / {sprint.total_points} puan tamamlandı
                </span>
              </button>
            )
          })}
        </section>

        <section aria-labelledby="backlog-title" className="grid content-start gap-3">
          <h3 id="backlog-title" className="flex items-center justify-between font-semibold text-brand">
            Backlog
            <span className="rounded-full bg-secondary px-2 text-sm font-medium text-secondary-foreground">
              {backlog.length} görev
            </span>
          </h3>

          <div className="overflow-hidden rounded-xl border bg-card">
            {isAdmin && checkedTasks.length > 0 && (
              <div className="flex items-center justify-between bg-secondary/60 px-4 py-3 text-sm font-medium text-secondary-foreground">
                <span>{checkedTasks.length} görev seçildi</span>
                <span>{checkedPoints} puan</span>
              </div>
            )}

            {backlogQuery.isPending ? (
              <div role="status" className="flex justify-center py-8">
                <Loader2Icon className="size-5 animate-spin text-primary" />
              </div>
            ) : backlog.length === 0 ? (
              <p className="p-6 text-center text-sm text-muted-foreground">
                Sprinte atanmamış açık görev yok.
              </p>
            ) : (
              <ul className="divide-y">
                {backlog.map((task) => (
                  <li key={task.id}>
                    <label
                      className={cn(
                        'flex items-center gap-3 px-4 py-3',
                        isAdmin && 'cursor-pointer hover:bg-muted/50',
                      )}
                    >
                      {isAdmin && (
                        <input
                          type="checkbox"
                          checked={checked.has(task.id)}
                          onChange={() => toggle(task.id)}
                          className="size-4 accent-primary"
                        />
                      )}
                      <span className="grid min-w-0 flex-1 gap-1">
                        <span className="truncate text-sm font-medium">{task.title}</span>
                        <span className="flex items-center gap-2 text-xs text-muted-foreground">
                          #{task.id}
                          {task.assignee && <UserAvatar user={task.assignee} className="size-5 text-[9px]" />}
                        </span>
                      </span>
                      <span className="shrink-0 text-sm font-medium text-brand">
                        {task.story_points === null ? '— puan' : `${task.story_points} puan`}
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
            )}

            {isAdmin && openSprints.length > 0 && backlog.length > 0 && (
              <div className="grid gap-3 border-t p-4">
                <Select value={target ? String(target.id) : undefined} onValueChange={(v) => setTargetId(Number(v))}>
                  <SelectTrigger className="w-full" aria-label="Görevlerin ekleneceği sprint">
                    <SelectValue placeholder="Sprint seç" />
                  </SelectTrigger>
                  <SelectContent>
                    {openSprints.map((sprint) => (
                      <SelectItem key={sprint.id} value={String(sprint.id)}>
                        {sprint.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {target && (
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>
                      {target.total_points} mevcut + {checkedPoints} seçilen
                    </span>
                    {target.capacity_points != null ? (
                      <span className={cn('font-medium', overCapacity && 'text-destructive')}>
                        {projected} / {target.capacity_points} puan
                      </span>
                    ) : (
                      <span>Kapasite sınırı yok</span>
                    )}
                  </div>
                )}

                <Button
                  className="justify-self-start"
                  disabled={!target || checkedTasks.length === 0 || addTasks.isPending}
                  onClick={() =>
                    target && addTasks.mutate({ sprintId: target.id, taskIds: checkedTasks.map((t) => t.id) })
                  }
                >
                  {addTasks.isPending ? <Loader2Icon className="animate-spin" /> : <PlusIcon />}
                  Sprinte ekle
                </Button>
              </div>
            )}
          </div>

          {/* Sözleşme 11.3: kapasite aşılsa da eklenebilir, önceden uyarılır */}
          {isAdmin && overCapacity && checkedTasks.length > 0 && target && (
            <div role="status" className="flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
              <TriangleAlertIcon className="mt-0.5 size-4 shrink-0" />
              <div className="grid gap-0.5">
                <span className="font-medium">
                  Sprint kapasitesi aşılıyor ({projected} / {target.capacity_points} puan).
                </span>
                <span>Seçilen görevler eklenirse kapasite {projected - (target.capacity_points ?? 0)} puan aşılır.</span>
              </div>
            </div>
          )}

          {backlogQuery.data && backlogQuery.data.length >= 100 && (
            <p className="text-xs text-muted-foreground">Backlog'daki ilk 100 açık görev gösteriliyor.</p>
          )}
        </section>
      </div>
    </div>
  )
}

interface SelectedSprintCardProps {
  sprint: Sprint
  tasks: Task[] | undefined
  loading: boolean
  canEdit: boolean
  removingId: number | undefined
  onRemove: (taskId: number) => void
}

function SelectedSprintCard({ sprint, tasks, loading, canEdit, removingId, onRemove }: SelectedSprintCardProps) {
  const phase = sprintPhase(sprint)
  const progress = sprint.total_points === 0 ? 0 : Math.min(100, sprint.progress_percent)

  return (
    <section aria-label={`${sprint.name} özeti`} className="grid gap-5 rounded-xl border bg-card p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="grid gap-1">
          <h3 className="flex items-center gap-2 text-xl font-semibold text-brand">
            {sprint.name}
            <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', PHASE_STYLES[phase])}>
              {PHASE_LABELS[phase]}
            </span>
          </h3>
          {sprint.goal && <p className="text-sm">{sprint.goal}</p>}
        </div>
        <span className="flex items-center gap-2 text-sm text-muted-foreground">
          <CalendarIcon className="size-4 text-primary" />
          {formatSprintRange(sprint.start_date, sprint.end_date)}
        </span>
      </div>

      <div className="grid gap-5 sm:grid-cols-[minmax(0,1fr)_auto]">
        <div className="grid gap-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">
              İlerleme · {sprint.done_points} / {sprint.total_points} puan
            </span>
            <span className="font-medium text-brand">%{formatPercent(progress)}</span>
          </div>
          <div
            role="progressbar"
            aria-label={`${sprint.name} ilerlemesi`}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progress}
            className="h-2 overflow-hidden rounded-full bg-secondary"
          >
            <div className="h-full rounded-full bg-primary" style={{ width: `${progress}%` }} />
          </div>
        </div>
        <div className="grid gap-0.5 sm:border-l sm:pl-5">
          <span className="text-xs text-muted-foreground">Mevcut kapasite</span>
          {sprint.capacity_points != null ? (
            <span
              className={cn(
                'text-2xl font-semibold text-brand',
                sprint.total_points > sprint.capacity_points && 'text-destructive',
              )}
            >
              {sprint.total_points} / {sprint.capacity_points}{' '}
              <span className="text-sm font-normal text-muted-foreground">puan</span>
            </span>
          ) : (
            <span className="text-sm">Kapasite tanımsız · {sprint.total_points} puan</span>
          )}
        </div>
      </div>

      <div className="grid gap-2 border-t pt-4">
        <h4 className="text-sm font-semibold">Sprintteki görevler {tasks && `(${tasks.length})`}</h4>
        {loading ? (
          <Loader2Icon className="size-4 animate-spin text-primary" />
        ) : !tasks || tasks.length === 0 ? (
          <p className="text-sm text-muted-foreground">Bu sprintte henüz görev yok.</p>
        ) : (
          <ul className="grid gap-1">
            {tasks.map((task) => (
              <li key={task.id} className="flex items-center gap-3 rounded-lg px-2 py-1.5 hover:bg-muted/50">
                <Link to={`/gorevler/${task.id}`} className="min-w-0 flex-1 truncate text-sm hover:underline">
                  {task.title}
                </Link>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {task.story_points === null ? '—' : `${task.story_points} puan`}
                </span>
                {canEdit && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-7 text-muted-foreground hover:text-destructive"
                    disabled={removingId === task.id}
                    onClick={() => onRemove(task.id)}
                    aria-label={`${task.title} görevini sprintten çıkar`}
                  >
                    {removingId === task.id ? <Loader2Icon className="animate-spin" /> : <XIcon />}
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}
