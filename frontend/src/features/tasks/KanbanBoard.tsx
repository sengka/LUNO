import { useState, type ReactNode } from 'react'
import {
  DndContext,
  DragOverlay,
  getClientRect,
  KeyboardSensor,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type ClientRect,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2Icon, PlusIcon } from 'lucide-react'
import { toast } from 'sonner'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/auth-context'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'
import { taskKeys, tasksApi } from './api'
import { TaskCard } from './TaskCard'
import { TaskCreateDialog } from './TaskCreateDialog'
import { TASK_STATUS_LABELS, type ActiveTaskStatus, type BoardResponse, type Task } from './types'

const COLUMN_DOT: Record<ActiveTaskStatus, string> = {
  TODO: 'bg-slate-400',
  IN_PROGRESS: 'bg-primary',
  REVIEW_TESTING: 'bg-amber-500',
  DONE: 'bg-emerald-500',
}

// Kartı panoda bir sütundan diğerine taşır (iyimser güncelleme için).
// Backend sütunları görev numarasına göre dizdiği için kart da o sıradaki yerine konur;
// böylece sunucudan güncel liste gelince kart yer değiştirmez. Sütun içi sıralama
// backend'e "position" alanı eklenince yapılacak.
function moveTask(board: BoardResponse, taskId: number, to: ActiveTaskStatus): BoardResponse {
  const task = board.columns.flatMap((column) => column.tasks).find((t) => t.id === taskId)
  if (!task) return board
  return {
    columns: board.columns.map((column) => {
      const tasks = column.tasks.filter((t) => t.id !== taskId)
      if (column.status !== to) return { ...column, tasks }
      return { ...column, tasks: [...tasks, { ...task, status: to }].sort((a, b) => a.id - b.id) }
    }),
  }
}

// Sürüklenen kartın asıl yeri gizlendiğinde (silüet kalmasın diye) ölçüsü 0 okunur ve
// DragOverlay imlecin soluna kayar. Bu yüzden kartın son görünür ölçüsü hatırlanır.
const lastVisibleRects = new WeakMap<HTMLElement, ClientRect>()
const measuring = {
  draggable: {
    measure: (element: HTMLElement) => {
      const rect = getClientRect(element, { ignoreTransform: true })
      if (rect.width === 0 && rect.height === 0) return lastVisibleRects.get(element) ?? rect
      lastVisibleRects.set(element, rect)
      return rect
    },
  },
}

// US-015 · Mockup: docs/tasarim/04-proje-detay-kanban.png
export function KanbanBoard({ projectId }: { projectId: number }) {
  const { isAdmin } = useAuth()
  const queryClient = useQueryClient()
  const boardKey = taskKeys.board(projectId)
  const [activeTask, setActiveTask] = useState<Task | null>(null)

  const boardQuery = useQuery({
    queryKey: boardKey,
    queryFn: () => tasksApi.board(projectId),
  })

  // Kart bırakıldığı anda yeni sütuna geçer (handleDragEnd); backend reddederse eski yerine döner (FR-043)
  const moveMutation = useMutation({
    mutationFn: ({ taskId, status }: { taskId: number; status: ActiveTaskStatus; previous?: BoardResponse }) =>
      tasksApi.updateStatus(taskId, status),
    onError: (error, { previous }) => {
      if (previous) queryClient.setQueryData(boardKey, previous)
      // 403 mesajı ortak uyarıyla gösterilir ("Size atanmamış bir görevin durumunu değiştiremezsiniz.")
      if (!(error instanceof ApiError && error.status === 403)) {
        toast.error(error instanceof ApiError ? error.message : 'Görev taşınamadı. Lütfen tekrar dene.')
      }
    },
    onSuccess: (task) => {
      queryClient.setQueryData(taskKeys.detail(task.id), task)
      // Proje ilerleme yüzdesi DONE sayısına göre değişir
      void queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: boardKey }),
  })

  const sensors = useSensors(
    // Birkaç piksel sürüklenmeden taşıma başlamasın: tıklama görev detayını açsın
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor),
  )

  const handleDragStart = ({ active }: DragStartEvent) => {
    setActiveTask((active.data.current?.task as Task | undefined) ?? null)
  }

  const handleDragEnd = ({ active, over }: DragEndEvent) => {
    setActiveTask(null)
    const task = active.data.current?.task as Task | undefined
    const target = over?.id as ActiveTaskStatus | undefined
    if (!task || !target || task.status === target) return

    // Panoyu aynı anda güncelle: kart bırakıldığı yerde kalsın, geri sekip tekrar gelmesin.
    // Arka planda süren bir yenileme bu güncellemenin üstüne yazmasın diye önce o iptal edilir.
    void queryClient.cancelQueries({ queryKey: boardKey })
    const previous = queryClient.getQueryData<BoardResponse>(boardKey)
    if (previous) queryClient.setQueryData(boardKey, moveTask(previous, task.id, target))
    moveMutation.mutate({ taskId: task.id, status: target, previous })
  }

  if (boardQuery.isPending) {
    return (
      <div role="status" className="flex justify-center py-16">
        <Loader2Icon className="size-6 animate-spin text-primary" />
        <span className="sr-only">Kanban panosu yükleniyor…</span>
      </div>
    )
  }

  if (boardQuery.isError) {
    return (
      <div className="grid gap-3">
        <Alert variant="destructive" role="alert">
          <AlertDescription>
            {boardQuery.error instanceof ApiError ? boardQuery.error.message : 'Kanban panosu alınamadı.'}
          </AlertDescription>
        </Alert>
        <Button variant="outline" className="justify-self-start" onClick={() => void boardQuery.refetch()}>
          Tekrar dene
        </Button>
      </div>
    )
  }

  return (
    <DndContext
      sensors={sensors}
      measuring={measuring}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDragCancel={() => setActiveTask(null)}
      accessibility={{
        screenReaderInstructions: {
          draggable: 'Görevi taşımak için boşluk tuşuna bas, ok tuşlarıyla sütun seç, bırakmak için tekrar boşluğa bas.',
        },
      }}
    >
      {/* Geniş ekranda 4 sütun, dar ekranda yatay kaydırma */}
      <div className="-mx-4 overflow-x-auto px-4 pb-2 sm:mx-0 sm:px-0">
        <div className="grid min-w-[56rem] grid-cols-4 gap-4">
          {boardQuery.data.columns.map((column) => (
            <KanbanColumn
              key={column.status}
              status={column.status}
              count={column.tasks.length}
              action={
                isAdmin && column.status === 'TODO' ? (
                  <TaskCreateDialog
                    projectId={projectId}
                    trigger={
                      <Button variant="ghost" size="icon" className="size-7" aria-label="To Do sütununa görev ekle">
                        <PlusIcon />
                      </Button>
                    }
                  />
                ) : null
              }
            >
              {column.tasks.length === 0 ? (
                <p className="rounded-xl border border-dashed p-4 text-center text-sm text-muted-foreground">
                  Görev yok
                </p>
              ) : (
                column.tasks.map((task) => <DraggableTask key={task.id} task={task} />)
              )}
            </KanbanColumn>
          ))}
        </div>
      </div>

      {/* Bırakma animasyonu kapalı: varsayılan animasyon kartı önce eski yerine kaydırıyordu */}
      <DragOverlay dropAnimation={null}>{activeTask && <TaskCard task={activeTask} dragging />}</DragOverlay>
    </DndContext>
  )
}

function KanbanColumn({
  status,
  count,
  action,
  children,
}: {
  status: ActiveTaskStatus
  count: number
  action: ReactNode
  children: ReactNode
}) {
  const { setNodeRef, isOver } = useDroppable({ id: status })

  return (
    <section aria-label={`${TASK_STATUS_LABELS[status]} sütunu`} className="grid content-start gap-3">
      <header className="flex h-8 items-center gap-2">
        <span className={cn('size-2 rounded-full', COLUMN_DOT[status])} />
        <h3 className="font-semibold">{TASK_STATUS_LABELS[status]}</h3>
        <span className="rounded-full bg-secondary px-2 text-xs font-medium text-secondary-foreground">{count}</span>
        <span className="ml-auto">{action}</span>
      </header>
      <div
        ref={setNodeRef}
        className={cn(
          'grid min-h-32 content-start gap-3 rounded-xl p-1 transition-colors',
          isOver && 'bg-secondary/60 ring-2 ring-primary/40',
        )}
      >
        {children}
      </div>
    </section>
  )
}

function DraggableTask({ task }: { task: Task }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: task.id,
    data: { task },
  })

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      aria-roledescription="sürüklenebilir görev"
      // Sürüklenirken eski yerinde silüet kalmasın; kartın kendisi DragOverlay'de imleçle gider
      className={cn('cursor-grab touch-none', isDragging && 'hidden')}
    >
      <TaskCard task={task} />
    </div>
  )
}
