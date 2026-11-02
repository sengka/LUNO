import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Trash2Icon } from 'lucide-react'
import { toast } from 'sonner'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/auth-context'
import { ApiError } from '@/lib/api'
import { filesApi } from './api'
import type { ProjectFile } from './types'

// US-035 · Mockup: docs/tasarim/mockup/dosyalar.png ("Dosyayı silmek istediğine emin misin?")
export function FileDeleteButton({ file, onDeleted }: { file: ProjectFile; onDeleted: () => void }) {
  const { user, isAdmin } = useAuth()
  const [confirmOpen, setConfirmOpen] = useState(false)

  const deletion = useMutation({
    mutationFn: () => filesApi.remove(file.id),
    // Hata aşağıda mesaj olarak gösterilir
    meta: { skipForbiddenToast: true },
    onSuccess: () => {
      setConfirmOpen(false)
      toast.success(`"${file.name}" silindi.`)
      onDeleted()
    },
    onError: (error) => {
      setConfirmOpen(false)
      if (error instanceof ApiError && error.status === 404) {
        toast.error('Dosya bulunamadı, daha önce silinmiş olabilir.')
        onDeleted()
      } else {
        toast.error(error instanceof ApiError ? error.message : 'Dosya silinemedi. Lütfen tekrar dene.')
      }
    },
  })

  // FR-049: Dosyayı yalnızca yükleyen kişi veya yönetici silebilir
  if (!isAdmin && file.uploaded_by.id !== user?.id) return null

  return (
    <>
      <Button
        variant="ghost"
        size="icon"
        className="text-destructive hover:text-destructive"
        onClick={() => setConfirmOpen(true)}
        aria-label={`${file.name} dosyasını sil`}
      >
        <Trash2Icon />
      </Button>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Dosyayı silmek istediğine emin misin?"
        description={
          <>
            <strong>“{file.name}”</strong> ve dosyaya ait yorumlar silinecek. Bu işlem geri alınamaz.
          </>
        }
        confirmLabel="Evet, dosyayı sil"
        pending={deletion.isPending}
        onConfirm={() => deletion.mutate()}
      />
    </>
  )
}
