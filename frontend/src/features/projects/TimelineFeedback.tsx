import { AccessDenied } from '@/components/AccessDenied'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { ApiError } from '@/lib/api'

export function TimelineError({ error, retry, fetching }: {
  error: Error; retry: () => void; fetching: boolean
}) {
  const status = error instanceof ApiError ? error.status : null
  if (status === 403) return <AccessDenied title="Bu projeye erişimin yok" description="Projeye eklenmek için proje yöneticine başvurabilirsin." backTo="/projeler" backLabel="Projelerime dön" />
  return <div className="grid gap-3">
    <Alert variant="destructive" role="alert"><AlertDescription>{status === 404 ? 'Proje bulunamadı.' : error instanceof ApiError ? error.message : 'Görünüm yüklenemedi.'}</AlertDescription></Alert>
    {status !== 404 && <Button className="justify-self-start" variant="outline" disabled={fetching} onClick={retry}>Tekrar dene</Button>}
  </div>
}

export function TimelineLegend() {
  return <ul aria-label="Görev durumları" className="flex flex-wrap gap-5 text-sm text-muted-foreground">
    {[['bg-slate-400', 'Yapılacak'], ['bg-amber-500', 'Devam ediyor'], ['bg-violet-500', 'İnceleme'], ['bg-emerald-500', 'Tamamlandı']].map(([color, label]) =>
      <li key={label} className="flex items-center gap-2"><span className={`size-2 rounded-full ${color}`} />{label}</li>)}
  </ul>
}
