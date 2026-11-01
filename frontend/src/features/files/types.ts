// Sözleşme 2. bölüm: File nesnesi
export interface ProjectFile {
  id: number
  name: string
  size_bytes: number
  mime_type: string
  project_id: number
  task_id: number | null
  uploaded_by: {
    id: number
    full_name: string
    avatar_url: string | null
  }
  comment_count: number
  created_at: string
}

// Sözleşme 8.1 (FR-047): izin verilen türler ve en büyük boyut
export const MAX_FILE_SIZE = 10 * 1024 * 1024
export const ALLOWED_EXTENSIONS = ['pdf', 'docx', 'xlsx', 'pptx', 'png', 'jpg', 'jpeg', 'txt'] as const
export const ALLOWED_TYPES_LABEL = 'PDF, DOCX, XLSX, PPTX, PNG, JPG, TXT'
