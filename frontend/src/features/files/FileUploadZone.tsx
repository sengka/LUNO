import { useId, useRef, useState, type DragEvent } from 'react'
import { CircleAlertIcon, CloudUploadIcon, FileIcon, XIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'
import { filesApi } from './api'
import { formatFileSize, validateFile } from './file-utils'
import { ALLOWED_TYPES_LABEL, type ProjectFile } from './types'

interface UploadItem {
  key: string
  name: string
  size: number
  progress: number
  error: string | null
}

interface FileUploadZoneProps {
  projectId: number
  taskId: number | null
  onUploaded: (file: ProjectFile) => void
}

// US-018 · Mockup: docs/tasarim/mockup/dosyalar.png (yükleme alanı ve yükleme durumu)
export function FileUploadZone({ projectId, taskId, onUploaded }: FileUploadZoneProps) {
  const inputId = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [items, setItems] = useState<UploadItem[]>([])

  const update = (key: string, patch: Partial<UploadItem>) =>
    setItems((current) => current.map((item) => (item.key === key ? { ...item, ...patch } : item)))

  const remove = (key: string) => setItems((current) => current.filter((item) => item.key !== key))

  const uploadOne = async (file: File) => {
    const key = `${file.name}-${file.size}-${crypto.randomUUID()}`
    const validationError = validateFile(file)
    setItems((current) => [
      ...current,
      { key, name: file.name, size: file.size, progress: 0, error: validationError },
    ])
    if (validationError) return

    try {
      const uploaded = await filesApi.upload(projectId, file, taskId, (progress) => update(key, { progress }))
      remove(key)
      onUploaded(uploaded)
    } catch (error) {
      update(key, {
        error: error instanceof ApiError ? error.message : 'Dosya yüklenemedi. Lütfen tekrar dene.',
      })
    }
  }

  // Seçilen dosyalar sırayla yüklenir
  const handleFiles = async (fileList: FileList | null) => {
    if (!fileList) return
    for (const file of Array.from(fileList)) await uploadOne(file)
  }

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setDragging(false)
    void handleFiles(event.dataTransfer.files)
  }

  return (
    <div className="grid gap-3">
      <div
        onDragOver={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={cn(
          'flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-6 text-center transition-colors sm:flex-row sm:text-left',
          dragging ? 'border-primary bg-secondary' : 'border-primary/40 bg-secondary/30',
        )}
      >
        <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-secondary text-primary">
          <CloudUploadIcon className="size-5" />
        </span>
        <div className="grid gap-0.5">
          <label htmlFor={inputId} className="cursor-pointer font-medium text-brand hover:underline">
            Dosyayı buraya sürükle veya seç
          </label>
          <p className="text-xs text-muted-foreground">{ALLOWED_TYPES_LABEL} · en fazla 10 MB</p>
        </div>
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          multiple
          accept=".pdf,.docx,.xlsx,.pptx,.png,.jpg,.jpeg,.txt"
          className="sr-only"
          onChange={(event) => {
            void handleFiles(event.target.files)
            // Aynı dosya tekrar seçilebilsin
            event.target.value = ''
          }}
        />
      </div>

      {items.length > 0 && (
        <ul className="grid gap-2" aria-label="Yüklenen dosyalar">
          {items.map((item) => (
            <li key={item.key} className="grid gap-2 rounded-xl border bg-card p-3">
              <div className="flex items-center gap-3">
                <FileIcon className="size-4 shrink-0 text-primary" />
                <div className="grid min-w-0 flex-1">
                  <span className="truncate text-sm font-medium">{item.name}</span>
                  <span className="text-xs text-muted-foreground">
                    {formatFileSize(item.size)} · {item.error ? 'Yüklenemedi' : 'Yükleniyor…'}
                  </span>
                </div>
                {item.error ? (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-7"
                    aria-label={`${item.name} uyarısını kapat`}
                    onClick={() => remove(item.key)}
                  >
                    <XIcon />
                  </Button>
                ) : (
                  <span className="text-sm font-medium text-brand">%{item.progress}</span>
                )}
              </div>

              {item.error ? (
                <p role="alert" className="flex items-center gap-2 rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  <CircleAlertIcon className="size-4 shrink-0" />
                  {item.error}
                </p>
              ) : (
                <div
                  role="progressbar"
                  aria-label={`${item.name} yükleniyor`}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={item.progress}
                  className="h-1.5 overflow-hidden rounded-full bg-secondary"
                >
                  <div className="h-full rounded-full bg-primary transition-[width]" style={{ width: `${item.progress}%` }} />
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
