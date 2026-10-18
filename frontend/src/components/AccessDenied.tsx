import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { ShieldAlertIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface AccessDeniedProps {
  title?: string
  description?: ReactNode
  backTo?: string
  backLabel?: string
}

// US-005: Erişim yetkisi olmayan sayfalar için ortak ekran (FR-013, 403 PROJECT_ACCESS_DENIED)
export function AccessDenied({
  title = 'Bu sayfaya erişimin yok',
  description = 'Bu içeriği görüntüleme yetkin bulunmuyor. Yanlışlık olduğunu düşünüyorsan proje yöneticine başvur.',
  backTo = '/',
  backLabel = 'Kontrol paneline dön',
}: AccessDeniedProps) {
  return (
    <div className="grid justify-items-center gap-3 rounded-xl border bg-card px-6 py-16 text-center">
      <span className="flex size-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
        <ShieldAlertIcon className="size-6" />
      </span>
      <h1 className="text-xl font-semibold">{title}</h1>
      <p className="max-w-md text-sm text-muted-foreground">{description}</p>
      <Button asChild variant="outline" className="mt-2">
        <Link to={backTo}>{backLabel}</Link>
      </Button>
    </div>
  )
}
