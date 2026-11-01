import { useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { XIcon } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet'
import { useAuth } from '@/features/auth/auth-context'
import { ApiError } from '@/lib/api'
import { taskKeys, tasksApi } from './api'
import { TaskDeleteButton } from './TaskDeleteButton'
import { TaskEditForm } from './TaskEditForm'
import { TaskLabels } from './TaskLabels'
import { TaskSubtasks } from './TaskSubtasks'
import { TaskComments } from '@/features/comments/TaskComments'

import { TaskAssigneeField, TaskStatusField } from './TaskDetailFields'
import { PRIORITY_LABELS } from './types'


function formatDate(value: string | null, timestamp = false) {
  if (!value) return 'Belirtilmedi'
  const date = new Date(timestamp ? value : `${value}T00:00:00`)
  if (Number.isNaN(date.getTime())) return 'Belirtilmedi'
  return new Intl.DateTimeFormat('tr-TR', { dateStyle: 'long' }).format(date)
}

function TaskDetailContent() {
  const { taskId } = useParams()
  const id = Number(taskId)
  const valid = Number.isSafeInteger(id) && id > 0
  const navigate = useNavigate()
  const location = useLocation()
  const { isAdmin } = useAuth()
  const [editing, setEditing] = useState(false)
  const query = useQuery({ queryKey: taskKeys.detail(id), queryFn: () => tasksApi.getDetail(id), enabled: valid, retry: false })
  const task = query.data
  const timelineFrom: unknown = location.state?.timelineFrom
  const backTo = task && typeof timelineFrom === 'string' &&
    [`/projeler/${task.project_id}/takvim`, `/projeler/${task.project_id}/gantt`].includes(timelineFrom)
    ? timelineFrom : task ? `/projeler/${task.project_id}` : '/projeler'
  let error: string | null = null
  if (!valid) error = 'Geçersiz görev numarası.'
  else if (query.isError) {
    const failure = query.error
    error = failure instanceof ApiError
      ? failure.status === 403 ? 'Bu görevi görüntüleme yetkin yok. Proje yöneticine başvurabilirsin.'
        : failure.status === 404 ? 'Görev bulunamadı. Silinmiş veya bağlantı geçersiz olabilir.' : failure.message
      : 'Görev bilgileri alınamadı. Lütfen tekrar dene.'
  }
  return (
    <>
      <p className="text-muted-foreground">Görev detayı</p>
      <Sheet open onOpenChange={(open) => { if (!open) navigate(backTo, { replace: true }) }}>
        <SheetContent showCloseButton={false} className="data-[side=right]:w-full data-[side=right]:sm:max-w-5xl gap-0">
          <header className="flex items-center justify-between gap-4 border-b px-6 py-4">
            <div>
              <SheetTitle className="text-primary">{task ? `Görev #${task.id}` : 'Görev detayı'}</SheetTitle>
              <SheetDescription>{task ? <Link to={backTo} className="underline">Projeye dön</Link> : 'Görev bilgileri'}</SheetDescription>
            </div>
            <Button variant="ghost" size="icon" asChild><Link to={backTo} replace aria-label="Görev detayını kapat"><XIcon /></Link></Button>
          </header>
          <div className="min-h-0 flex-1 overflow-y-auto p-6 sm:p-8">
            {valid && query.isPending && <p role="status">Görev bilgileri yükleniyor…</p>}
            {error && <div className="grid gap-4">
              <Alert variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>
              {valid && query.isError && !(query.error instanceof ApiError && [403, 404].includes(query.error.status)) && (
                <Button variant="outline" disabled={query.isFetching} onClick={() => void query.refetch()} className="justify-self-start">Tekrar dene</Button>
              )}
              <Link to={backTo} className="underline">{task ? 'Projeye dön' : 'Projelerime dön'}</Link>
            </div>}
            {!error && task && <div className="grid gap-8 md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
              <section className="min-w-0">
                <h1 className="break-words text-2xl font-semibold text-primary">{task.title}</h1>
                <p className="mt-2 text-sm text-muted-foreground">{task.created_by?.full_name ?? 'Bilinmeyen kullanıcı'} oluşturdu · {formatDate(task.created_at, true)}</p>
                <div className="mt-8">
                  {isAdmin && editing ? <TaskEditForm key={task.id} task={task} onClose={() => setEditing(false)} /> : <>
                    <h2 className="mb-3 text-lg font-semibold">Açıklama</h2>
                    <p className="whitespace-pre-wrap break-words text-muted-foreground">{task.description || 'Bu görev için açıklama eklenmemiş.'}</p>
                  </>}
                </div>
                <TaskSubtasks key={task.id} task={task} />
                <TaskComments key={`comments-${task.id}`} task={task} />
              </section>
              <aside className="border-t pt-6 md:border-t-0 md:border-l md:pt-0 md:pl-6" aria-label="Görev bilgileri">
                <h2 className="mb-6 text-lg font-semibold text-primary">Görev bilgileri</h2>
                <dl className="grid gap-6 text-sm">

                  <TaskStatusField task={task} />
                  <TaskAssigneeField task={task} />
                  {[

                    ['Başlangıç tarihi', formatDate(task.start_date)], ['Teslim tarihi', formatDate(task.due_date)],
                  ].map(([label, value]) => <div key={label}><dt className="text-muted-foreground">{label}</dt><dd className="mt-2 break-words rounded-xl border p-3">{value}</dd></div>)}
                  <div>
                    <dt className="text-muted-foreground">Öncelik</dt>
                    <dd className="mt-2">
                      {task.priority === null ? 'Belirtilmedi' : <Badge variant={task.priority === 'YUKSEK' ? 'destructive' : task.priority === 'ORTA' ? 'secondary' : 'outline'}>{PRIORITY_LABELS[task.priority]}</Badge>}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Efor puanı</dt>
                    <dd className="mt-2">{task.story_points === null ? 'Belirtilmedi' : <Badge variant="outline">{task.story_points} puan</Badge>}</dd>
                  </div>
                </dl>
                <TaskLabels key={task.id} task={task} />
              </aside>
            </div>}
          </div>
          {!error && task && <footer className="flex flex-wrap items-center justify-between gap-4 border-t p-6">
            <p className="text-sm text-muted-foreground">Son güncelleme: {formatDate(task.updated_at, true)}</p>
            {isAdmin && !editing && <div className="flex gap-2"><Button variant="outline" onClick={() => setEditing(true)}>Düzenle</Button><TaskDeleteButton task={task} /></div>}
          </footer>}
        </SheetContent>
      </Sheet>
    </>
  )
}

export function TaskDetailPage() {
  const { taskId } = useParams()
  return <TaskDetailContent key={taskId} />
}
