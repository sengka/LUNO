import { useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { ApiError } from '@/lib/api'
import { taskKeys, tasksApi } from './api'
import type { Task } from './types'

export function TaskDeleteButton({ task }: { task: Task }) {
  const [open, setOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const submitting = useRef(false)
  const cancelButton = useRef<HTMLButtonElement>(null)
  const client = useQueryClient()
  const navigate = useNavigate()
  const deletion = useMutation({
    mutationFn: () => tasksApi.remove(task.id),
    meta: { skipForbiddenToast: true },
    onSuccess: async () => {
      await client.cancelQueries({ queryKey: taskKeys.all })
      // Silinen görevin alt görevleri de artık mevcut değil. Projedeki detayları
      // kaldır; sonraki açılışta silinmiş bir alt görevi önbellekten gösterme.
      client.removeQueries({ queryKey: taskKeys.all, predicate: (query) =>
        query.queryKey[1] === 'detail' && (
          query.queryKey[2] === task.id ||
          (query.state.data as Task | undefined)?.project_id === task.project_id
        ),
      })
      void client.invalidateQueries({ queryKey: taskKeys.all })
      void client.invalidateQueries({ queryKey: ['projects'] })
      toast.success('Görev silindi.')
      navigate(`/projeler/${task.project_id}`, { replace: true })
    },
    onError: (failure) => setError(failure instanceof ApiError
      ? failure.status === 403 ? 'Bu görevi silme yetkin yok.'
        : failure.status === 404 ? 'Görev bulunamadı. Daha önce silinmiş olabilir.' : failure.message
      : 'Görev silinemedi. Lütfen tekrar dene.'),
    onSettled: () => { submitting.current = false },
  })
  return (
    <Dialog open={open} onOpenChange={(value) => {
      if (submitting.current) return
      setError(null)
      setOpen(value)
    }}>
      <DialogTrigger asChild><Button variant="destructive">Sil</Button></DialogTrigger>
      <DialogContent showCloseButton={!deletion.isPending}
        onEscapeKeyDown={(event) => { if (submitting.current) event.preventDefault() }}
        onInteractOutside={(event) => { if (submitting.current) event.preventDefault() }}
        onOpenAutoFocus={(event) => {
        event.preventDefault()
        cancelButton.current?.focus()
      }}>
        <DialogHeader>
          <DialogTitle>Görevi silmek istediğine emin misin?</DialogTitle>
          <DialogDescription className="break-words">“{task.title}” göreviyle birlikte alt görevler, yorumlar ve dosyalar da silinecek. Bu işlem geri alınamaz.</DialogDescription>
        </DialogHeader>
        {error && <Alert variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}
        <DialogFooter>
          <Button ref={cancelButton} variant="outline" disabled={deletion.isPending} onClick={() => {
            if (!submitting.current) setOpen(false)
          }}>Vazgeç</Button>
          <Button variant="destructive" disabled={deletion.isPending} onClick={() => {
            if (submitting.current) return
            submitting.current = true
            setError(null)
            deletion.mutate()
          }}>{deletion.isPending ? 'Siliniyor…' : 'Görevi sil'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
