import { useId, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { ApiError } from '@/lib/api'
import { projectsApi } from './api'
import type { Project } from './types'

interface Props {
  project: Project
}

export function ProjectDeleteButton({ project }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  const descriptionId = useId()
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const deletion = useMutation({
    mutationFn: () => projectsApi.remove(project.id),
    meta: { skipForbiddenToast: true },

    onSuccess: () => {
      dialogRef.current?.close()

      queryClient.removeQueries({
        queryKey: ['projects', 'detail', project.id],
        exact: true,
      })

      void queryClient.invalidateQueries({
        queryKey: ['projects'],
      })

      toast.success('Proje silindi.')
      navigate('/projeler', { replace: true })
    },

    onError: (error) => {
      if (error instanceof ApiError) {
        if (error.status === 403) {
          setErrorMessage('Bu projeyi silme yetkin yok.')
        } else if (error.status === 404) {
          setErrorMessage(
            'Proje bulunamadı. Daha önce silinmiş olabilir.',
          )
        } else {
          setErrorMessage(error.message)
        }
      } else {
        setErrorMessage('Proje silinemedi. Lütfen tekrar dene.')
      }
    },
  })

  const openDialog = () => {
    setErrorMessage(null)
    dialogRef.current?.showModal()
  }

  return (
    <>
      <Button
        type="button"
        variant="destructive"
        onClick={openDialog}
      >
        Projeyi sil
      </Button>

      <dialog
        ref={dialogRef}
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        onCancel={(event) => {
          if (deletion.isPending) event.preventDefault()
        }}
        className="fixed inset-0 m-auto max-h-[90svh] w-[calc(100%-2rem)] max-w-lg overflow-y-auto rounded-xl border bg-background p-6 text-foreground shadow-xl backdrop:bg-black/50"
      >
        <div className="grid gap-5">
          <h2 id={titleId} className="text-xl font-semibold">
            Projeyi silmek istediğine emin misin?
          </h2>

          <p
            id={descriptionId}
            className="break-words text-sm text-muted-foreground"
          >
            “{project.name}” projesi ve projeye bağlı görevler,
            dosyalar, yorumlar ve sprintler silinecek.
            Bu işlem geri alınamaz.
          </p>

          {errorMessage && (
            <Alert variant="destructive" role="alert">
              <AlertDescription>{errorMessage}</AlertDescription>
            </Alert>
          )}

          <div className="flex flex-wrap justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              autoFocus
              disabled={deletion.isPending}
              onClick={() => dialogRef.current?.close()}
            >
              Vazgeç
            </Button>

            <Button
              type="button"
              variant="destructive"
              disabled={deletion.isPending}
              onClick={() => {
                setErrorMessage(null)
                deletion.mutate()
              }}
            >
              {deletion.isPending ? 'Siliniyor…' : 'Evet, projeyi sil'}
            </Button>
          </div>
        </div>
      </dialog>
    </>
  )
}