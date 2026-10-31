import { api } from '@/lib/api'
import type { Paginated } from '@/types/api'
import type { Comment } from './types'

export const COMMENTS_PAGE_SIZE = 50

export const commentKeys = {
  task: (taskId: number) => ['comments', 'task', taskId] as const,
}

// Sözleşme 8.5: Görev yorumları eskiden yeniye sıralı ve sayfalı döner
export const commentsApi = {
  listForTask: (taskId: number, page: number) =>
    api.get<Paginated<Comment>>(`/tasks/${taskId}/comments?page=${page}&limit=${COMMENTS_PAGE_SIZE}`),
  addToTask: (taskId: number, body: string) => api.post<Comment>(`/tasks/${taskId}/comments`, { body }),
}
