import { FileIcon, FileSpreadsheetIcon, FileTextIcon, ImageIcon, PresentationIcon, type LucideIcon } from 'lucide-react'
import { ALLOWED_EXTENSIONS, ALLOWED_TYPES_LABEL, MAX_FILE_SIZE } from './types'

export function extensionOf(name: string) {
  const dot = name.lastIndexOf('.')
  return dot === -1 ? '' : name.slice(dot + 1).toLowerCase()
}

// 482133 → "471 KB", 1887436 → "1,8 MB"
export function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toLocaleString('tr-TR', { maximumFractionDigits: 1 })} MB`
}

// Yüklemeden önce istemcide kontrol (backend de ayrıca kontrol eder: 413 / 415)
export function validateFile(file: File): string | null {
  if (!(ALLOWED_EXTENSIONS as readonly string[]).includes(extensionOf(file.name))) {
    return `Desteklenen formatlar: ${ALLOWED_TYPES_LABEL}.`
  }
  if (file.size > MAX_FILE_SIZE) return 'Dosya en fazla 10 MB olabilir.'
  if (file.size === 0) return 'Dosya boş.'
  return null
}

interface FileKind {
  icon: LucideIcon
  className: string
}

// Mockup'taki tür ikonları ve renkleri (docs/tasarim/mockup/dosyalar.png)
export function fileKind(name: string): FileKind {
  switch (extensionOf(name)) {
    case 'pdf':
      return { icon: FileTextIcon, className: 'bg-red-50 text-red-500' }
    case 'png':
    case 'jpg':
    case 'jpeg':
      return { icon: ImageIcon, className: 'bg-secondary text-primary' }
    case 'xlsx':
      return { icon: FileSpreadsheetIcon, className: 'bg-emerald-50 text-emerald-600' }
    case 'pptx':
      return { icon: PresentationIcon, className: 'bg-amber-50 text-amber-600' }
    case 'docx':
      return { icon: FileTextIcon, className: 'bg-sky-50 text-sky-600' }
    default:
      return { icon: FileIcon, className: 'bg-muted text-muted-foreground' }
  }
}
