import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/auth-context'
import { ApiError } from '@/lib/api'
import { membersApi } from './members-api'

function InviteAcceptContent({ token }: { token: string }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const acceptance = useMutation({
    mutationFn: () => membersApi.acceptInvite(token),
    retry: false,
    onSuccess: (project) => {
      void queryClient.invalidateQueries({
        queryKey: ['projects'],
      })
      queryClient.setQueryData(
        ['projects', 'detail', project.id],
        project,
      )
      toast.success('Projeye katıldın.')
      navigate(`/projeler/${project.id}`, { replace: true })
    },
  })

  const error = acceptance.error
  const invalid =
    error instanceof ApiError && error.code === 'INVITE_INVALID'
  const alreadyMember =
    error instanceof ApiError && error.code === 'ALREADY_MEMBER'

  const errorMessage =
    invalid
      ? 'Davet bağlantısı geçersiz veya süresi dolmuş. Proje yöneticisinden yeni bir bağlantı iste.'
      : alreadyMember
        ? 'Zaten bu projenin üyesisin. Projelerim sayfasından projeyi açabilirsin.'
        : error instanceof ApiError
          ? error.message
          : 'Davet kabul edilemedi. Lütfen tekrar dene.'

  return (
    <section className="mx-auto grid max-w-xl gap-5 rounded-xl border bg-card p-6">
      <h1 className="text-2xl font-semibold">Proje daveti</h1>

      <p className="text-sm text-muted-foreground">
        {user?.email} hesabıyla giriş yaptın. Bu daveti kabul ederek
        ilgili projenin ekibine katılabilirsin.
      </p>

      {acceptance.isError && (
        <Alert variant="destructive" role="alert">
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      )}

      <div className="flex flex-wrap gap-2">
        {!invalid && !alreadyMember && (
          <Button
            type="button"
            disabled={acceptance.isPending}
            onClick={() => acceptance.mutate()}
          >
            {acceptance.isPending ? 'Katılınıyor…' : 'Daveti kabul et'}
          </Button>
        )}

        <Button variant="outline" asChild>
          <Link to="/projeler">Projelerim</Link>
        </Button>
      </div>
    </section>
  )
}

export function InviteAcceptPage() {
  const { token } = useParams()

  if (!token) {
    return (
      <Alert variant="destructive" role="alert">
        <AlertDescription>Davet bağlantısı eksik.</AlertDescription>
      </Alert>
    )
  }

  return <InviteAcceptContent key={token} token={token} />
}