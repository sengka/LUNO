import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { UserAvatar } from '@/components/UserAvatar'
import { useAuth } from '@/features/auth/auth-context'
import { ApiError } from '@/lib/api'
import { taskKeys, tasksApi } from './api'
import { AssigneeSelect } from './AssigneeSelect'
import { BOARD_STATUSES, TASK_STATUS_LABELS, type ActiveTaskStatus, type Task } from './types'

const valueBox = 'mt-2 break-words rounded-xl border p-3'

function useTaskUpdated(task: Task) {
  const queryClient = useQueryClient()
  return (updated: Task) => {
    queryClient.setQueryData(taskKeys.detail(task.id), updated)
    // Kanban ve proje ilerlemesi de güncel kalsın
    void queryClient.invalidateQueries({ queryKey: taskKeys.board(task.project_id) })
    void queryClient.invalidateQueries({ queryKey: ['projects'] })
  }
}

// US-014: Görev durumunu yalnızca atanan kişi veya yönetici değiştirir (FR-033, FR-034)
export function TaskStatusField({ task }: { task: Task }) {
  const { user, isAdmin } = useAuth()
  const onUpdated = useTaskUpdated(task)
  const [error, setError] = useState<string | null>(null)

  const isActive = (BOARD_STATUSES as string[]).includes(task.status)
  const canChange = isActive && (isAdmin || task.assignee?.id === user?.id)

  const mutation = useMutation({
    mutationFn: (status: ActiveTaskStatus) => tasksApi.updateStatus(task.id, status),
    // 403 mesajı aşağıda alanın altında gösterilir
    meta: { skipForbiddenToast: true },
    onSuccess: (updated) => {
      setError(null)
      onUpdated(updated)
      toast.success(`Görev "${TASK_STATUS_LABELS[updated.status]}" durumuna taşındı.`)
    },
    onError: (failure) => {
      if (failure instanceof ApiError && failure.code === 'NOT_TASK_ASSIGNEE') {
        setError('Bu görev sana atanmadığı için durumunu değiştiremezsin. Görevin sorumlusu veya bir yönetici değiştirebilir.')
      } else if (failure instanceof ApiError && failure.code === 'TASK_NOT_ACTIVE') {
        setError('Onay bekleyen veya reddedilen görevin durumu değiştirilemez.')
      } else {
        setError(failure instanceof ApiError ? failure.message : 'Durum değiştirilemedi. Lütfen tekrar dene.')
      }
    },
  })

  return (
    <div>
      <dt className="text-muted-foreground">Durum</dt>
      {canChange ? (
        <dd className="mt-2">
          <Select
            value={task.status}
            onValueChange={(status) => {
              setError(null)
              mutation.mutate(status as ActiveTaskStatus)
            }}
            disabled={mutation.isPending}
          >
            <SelectTrigger className="w-full" aria-label="Görev durumu">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {BOARD_STATUSES.map((status) => (
                <SelectItem key={status} value={status}>
                  {TASK_STATUS_LABELS[status]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </dd>
      ) : (
        <>
          <dd className={valueBox}>{TASK_STATUS_LABELS[task.status]}</dd>
          {isActive && (
            <p className="mt-1.5 text-xs text-muted-foreground">Durumu görevin sorumlusu veya bir yönetici değiştirebilir.</p>
          )}
        </>
      )}
      {error && (
        <p role="alert" className="mt-1.5 text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  )
}

// US-012: Yönetici görevi proje üyelerinden birine atar (FR-030)
export function TaskAssigneeField({ task }: { task: Task }) {
  const { isAdmin } = useAuth()
  const onUpdated = useTaskUpdated(task)
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: (assigneeId: number | null) => tasksApi.updateAssignee(task.id, assigneeId),
    meta: { skipForbiddenToast: true },
    onSuccess: (updated) => {
      setError(null)
      onUpdated(updated)
      toast.success(updated.assignee ? `Görev ${updated.assignee.full_name} kişisine atandı.` : 'Görevin ataması kaldırıldı.')
    },
    onError: (failure) => {
      setError(failure instanceof ApiError ? failure.message : 'Atama yapılamadı. Lütfen tekrar dene.')
    },
  })

  return (
    <div>
      <dt className="text-muted-foreground">Sorumlu</dt>
      {isAdmin ? (
        <dd className="mt-2">
          <AssigneeSelect
            projectId={task.project_id}
            value={task.assignee?.id ?? null}
            onChange={(assigneeId) => {
              setError(null)
              mutation.mutate(assigneeId)
            }}
            disabled={mutation.isPending}
          />
        </dd>
      ) : (
        <dd className={`${valueBox} flex items-center gap-2`}>
          {task.assignee ? (
            <>
              <UserAvatar user={task.assignee} className="size-6 text-[10px]" />
              {task.assignee.full_name}
            </>
          ) : (
            'Atanmamış'
          )}
        </dd>
      )}
      {error && (
        <p role="alert" className="mt-1.5 text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  )
}
