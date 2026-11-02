import { useQuery, useQueryClient } from '@tanstack/react-query'
import { FolderOpenIcon, Loader2Icon } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { taskKeys } from '@/features/tasks/api'
import type { Task } from '@/features/tasks/types'
import { ApiError } from '@/lib/api'
import { fileKeys, filesApi } from './api'
import { FileRow } from './FileRow'
import { FileUploadZone } from './FileUploadZone'

// Görev detayındaki "Dosyalar" bölümü · Mockup: docs/tasarim/05-gorev-detay.png
export function TaskFiles({ task }: { task: Task }) {
  const queryClient = useQueryClient()

  const filesQuery = useQuery({
    queryKey: fileKeys.task(task.id),
    queryFn: () => filesApi.listForTask(task.project_id, task.id),
    retry: false,
  })

  const files = filesQuery.data?.items ?? []
  const total = filesQuery.data?.total ?? task.file_count

  // Dosya listesi, görev detayındaki ve Kanban kartındaki dosya sayısı güncellensin
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: fileKeys.task(task.id) })
    void queryClient.invalidateQueries({ queryKey: taskKeys.detail(task.id) })
    void queryClient.invalidateQueries({ queryKey: taskKeys.board(task.project_id) })
  }

  return (
    <section aria-labelledby="task-files-title" className="mt-10 grid gap-4">
      <h2 id="task-files-title" className="flex items-center gap-2 text-lg font-semibold text-brand">
        Dosyalar
        <span className="rounded-full bg-secondary px-2 text-sm font-medium text-secondary-foreground">{total}</span>
      </h2>

      {filesQuery.isPending ? (
        <div role="status" className="flex justify-center py-4">
          <Loader2Icon className="size-5 animate-spin text-primary" />
          <span className="sr-only">Dosyalar yükleniyor…</span>
        </div>
      ) : filesQuery.isError ? (
        <div className="grid gap-3">
          <Alert variant="destructive" role="alert">
            <AlertDescription>
              {filesQuery.error instanceof ApiError ? filesQuery.error.message : 'Dosyalar alınamadı.'}
            </AlertDescription>
          </Alert>
          <Button variant="outline" className="justify-self-start" onClick={() => void filesQuery.refetch()}>
            Tekrar dene
          </Button>
        </div>
      ) : files.length === 0 ? (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <FolderOpenIcon className="size-4" />
          Henüz dosya yok. İlk dosyayı yükleyerek başla.
        </p>
      ) : (
        <ul className="grid gap-2">
          {files.map((file) => (
            <FileRow key={file.id} file={file} onDeleted={refresh} />
          ))}
        </ul>
      )}

      {/* US-018: Projenin her üyesi dosya yükleyebilir (sözleşme 8.1) */}
      <FileUploadZone projectId={task.project_id} taskId={task.id} onUploaded={refresh} />
    </section>
  )
}
