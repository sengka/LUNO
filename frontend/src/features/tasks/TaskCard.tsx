import { Link } from 'react-router'
import { CalendarIcon, MessageCircleIcon, PaperclipIcon } from 'lucide-react'
import { UserAvatar } from '@/components/UserAvatar'
import { cn } from '@/lib/utils'
import { PRIORITY_LABELS, type Task, type TaskPriority } from './types'

const PRIORITY_STYLES: Record<TaskPriority, string> = {
  YUKSEK: 'bg-red-50 text-red-600',
  ORTA: 'bg-amber-50 text-amber-600',
  DUSUK: 'bg-emerald-50 text-emerald-600',
}

const PRIORITY_DOT: Record<TaskPriority, string> = {
  YUKSEK: 'bg-red-500',
  ORTA: 'bg-amber-500',
  DUSUK: 'bg-emerald-500',
}

const dateFormatter = new Intl.DateTimeFormat('tr-TR', { day: '2-digit', month: 'short', year: 'numeric' })

function isOverdue(task: Task) {
  if (!task.due_date || task.status === 'DONE') return false
  const today = new Date().toISOString().slice(0, 10)
  return task.due_date < today
}

// Mockup: docs/tasarim/04-proje-detay-kanban.png (görev kartı)
export function TaskCard({ task, dragging = false }: { task: Task; dragging?: boolean }) {
  const label = task.labels[0]
  const done = task.status === 'DONE'
  const progress = task.subtask_count > 0
    ? Math.min(100, Math.max(0, task.subtask_done_count / task.subtask_count * 100)) : 0

  return (
    <Link
      to={`/gorevler/${task.id}`}
      // Sürükleme sırasında tıklama sayılmasın
      onClick={(event) => dragging && event.preventDefault()}
      draggable={false}
      className={cn(
        'grid gap-3 rounded-xl border bg-card p-4 text-left shadow-xs transition-colors hover:border-primary focus-visible:outline-2 focus-visible:outline-ring',
        dragging && 'rotate-1 cursor-grabbing border-primary shadow-lg',
      )}
    >
      <div className="flex items-start justify-between gap-2">
        {label ? (
          <span
            className="truncate rounded-md px-2 py-0.5 text-xs font-medium"
            style={{ backgroundColor: `${label.color}1a`, color: label.color }}
          >
            {label.name}
          </span>
        ) : (
          <span />
        )}
        {task.story_points !== null && (
          <span
            className="flex size-6 shrink-0 items-center justify-center rounded-full bg-secondary text-xs font-semibold text-secondary-foreground"
            title={`${task.story_points} efor puanı`}
          >
            {task.story_points}
          </span>
        )}
      </div>

      <p className={cn('break-words font-semibold leading-snug', done && 'text-muted-foreground')}>{task.title}</p>

      {task.priority && (
        <span
          className={cn(
            'flex w-fit items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-medium',
            PRIORITY_STYLES[task.priority],
          )}
        >
          <span className={cn('size-1.5 rounded-full', PRIORITY_DOT[task.priority])} />
          {PRIORITY_LABELS[task.priority]}
        </span>
      )}

      {task.subtask_count > 0 && <div className="grid gap-1.5">
        <span className="text-xs text-muted-foreground">{task.subtask_done_count}/{task.subtask_count} alt görev tamamlandı</span>
        <div role="progressbar" aria-label="Alt görev ilerlemesi" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}
          className="h-1.5 overflow-hidden rounded-full bg-secondary">
          <div className="h-full bg-primary" style={{ width: `${progress}%` }} />
        </div>
      </div>}

      <div className="flex items-center justify-between gap-2">
        {task.assignee ? (
          <UserAvatar user={task.assignee} className="size-7 text-xs" />
        ) : (
          <span className="text-xs text-muted-foreground">Atanmamış</span>
        )}
        <span className="flex items-center gap-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1" title="Yorum sayısı">
            <MessageCircleIcon className="size-3.5" />
            {task.comment_count}
          </span>
          <span className="flex items-center gap-1" title="Dosya sayısı">
            <PaperclipIcon className="size-3.5" />
            {task.file_count}
          </span>
        </span>
      </div>

      {task.due_date && (
        <span
          className={cn(
            'flex items-center gap-1.5 text-xs text-muted-foreground',
            isOverdue(task) && 'font-medium text-destructive',
          )}
        >
          <CalendarIcon className="size-3.5" />
          {dateFormatter.format(new Date(`${task.due_date}T00:00:00`))}
        </span>
      )}
    </Link>
  )
}
