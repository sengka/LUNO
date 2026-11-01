import { useState } from 'react'
import { DownloadIcon, Loader2Icon } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { UserAvatar } from '@/components/UserAvatar'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'
import { filesApi } from './api'
import { FileDeleteButton } from './FileDeleteButton'
import { extensionOf, fileKind, formatFileSize } from './file-utils'
import type { ProjectFile } from './types'

const dateFormatter = new Intl.DateTimeFormat('tr-TR', { day: 'numeric', month: 'short', year: 'numeric' })

// US-019: Dosya satırı ve indirme · Mockup: docs/tasarim/mockup/dosyalar.png
export function FileRow({ file, onDeleted }: { file: ProjectFile; onDeleted: () => void }) {
  const [downloading, setDownloading] = useState(false)
  const kind = fileKind(file.name)

  const handleDownload = async () => {
    setDownloading(true)
    try {
      await filesApi.download(file)
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Dosya indirilemedi. Lütfen tekrar dene.')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <li className="flex items-center gap-3 rounded-xl border bg-card p-3">
      <span className={cn('flex size-10 shrink-0 items-center justify-center rounded-lg', kind.className)}>
        <kind.icon className="size-5" />
      </span>

      <div className="grid min-w-0 flex-1 gap-0.5">
        <span className="truncate text-sm font-medium" title={file.name}>
          {file.name}
        </span>
        <span className="flex flex-wrap items-center gap-x-1.5 text-xs text-muted-foreground">
          <span className="uppercase">{extensionOf(file.name)}</span>·<span>{formatFileSize(file.size_bytes)}</span>·
          <time dateTime={file.created_at}>{dateFormatter.format(new Date(file.created_at))}</time>
        </span>
      </div>

      <span className="hidden items-center gap-2 text-xs text-muted-foreground sm:flex" title="Yükleyen">
        <UserAvatar user={file.uploaded_by} className="size-6 text-[10px]" />
        <span className="max-w-32 truncate">{file.uploaded_by.full_name}</span>
      </span>

      <div className="flex shrink-0 items-center">
        <Button
          variant="ghost"
          size="icon"
          disabled={downloading}
          onClick={() => void handleDownload()}
          aria-label={`${file.name} dosyasını indir`}
        >
          {downloading ? <Loader2Icon className="animate-spin" /> : <DownloadIcon />}
        </Button>
        <FileDeleteButton file={file} onDeleted={onDeleted} />
      </div>
    </li>
  )
}
