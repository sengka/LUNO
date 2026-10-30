// Sözleşme 2. bölüm: Comment nesnesi. Yorum ya göreve ya da dosyaya bağlıdır (FR-050).
export interface Comment {
  id: number
  body: string
  author: {
    id: number
    full_name: string
    avatar_url: string | null
  }
  task_id: number | null
  file_id: number | null
  created_at: string
}

export const COMMENT_MAX_LENGTH = 2000
