import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ApiError } from '@/lib/api'
import { membersApi } from './members-api'

export function ProjectInvitePanel({ projectId }: { projectId: number }) {
  const [copyError, setCopyError] = useState<string | null>(null)

  const invite = useMutation({
    mutationFn: () => membersApi.createInvite(projectId),
    retry: false,
    onSuccess: () => {
      setCopyError(null)
      toast.success('Davet bağlantısı oluşturuldu.')
    },
  })

  const copyLink = async () => {
    if (!invite.data) return

    setCopyError(null)

    try {
      await navigator.clipboard.writeText(invite.data.invite_url)
      toast.success('Davet bağlantısı kopyalandı.')
    } catch {
      setCopyError(
        'Otomatik kopyalama yapılamadı. Bağlantı alanını seçip Ctrl + C ile kopyalayabilirsin.',
      )
    }
  }

  return (
    <section
      aria-labelledby="project-invite-title"
      className="grid gap-4 rounded-xl border bg-card p-5 sm:p-6"
    >
      <div>
        <h2 id="project-invite-title" className="text-lg font-semibold">
          Davet bağlantısı
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Bağlantıyı paylaştığın kişiler giriş yaparak projeye katılabilir.
          Davet bağlantısı 7 gün geçerlidir.
        </p>
      </div>

      <Button
        type="button"
        variant="outline"
        className="justify-self-start"
        disabled={invite.isPending}
        onClick={() => {
          setCopyError(null)
          invite.mutate()
        }}
      >
        {invite.isPending
          ? 'Oluşturuluyor…'
          : invite.data
            ? 'Yeni davet bağlantısı oluştur'
            : 'Davet bağlantısı oluştur'}
      </Button>

      {invite.isError && (
        <Alert variant="destructive" role="alert">
          <AlertDescription>
            {invite.error instanceof ApiError
              ? invite.error.message
              : 'Davet bağlantısı oluşturulamadı.'}
          </AlertDescription>
        </Alert>
      )}

      {invite.data && (
        <div className="grid gap-3">
          <label htmlFor="project-invite-url" className="text-sm font-medium">
            Paylaşılacak bağlantı
          </label>

          <div className="flex flex-col gap-2 sm:flex-row">
            <Input
              id="project-invite-url"
              readOnly
              value={invite.data.invite_url}
              onFocus={(event) => event.currentTarget.select()}
            />
            <Button
              type="button"
              disabled={invite.isPending}
              onClick={() => void copyLink()}
            >
              Kopyala
            </Button>
          </div>

          <p className="text-sm text-muted-foreground">
            Geçerlilik sonu:{' '}
            {new Date(invite.data.expires_at).toLocaleString('tr-TR')}
          </p>
        </div>
      )}

      {copyError && (
        <p role="status" className="text-sm text-muted-foreground">
          {copyError}
        </p>
      )}
    </section>
  )
}