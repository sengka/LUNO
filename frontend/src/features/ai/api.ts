import { api } from '@/lib/api'
import type { CommentSummary, PointsSuggestion, WeeklySummary } from './types'

// Sözleşme 13: LLM uç noktaları yalnızca öneri döndürür, hiçbir şey kaydetmez.
// Kullanıcı onaylarsa normal uç noktalar (ör. görev güncelleme) çağrılır.
export const aiApi = {
  suggestPoints: (taskId: number) => api.post<PointsSuggestion>(`/ai/tasks/${taskId}/suggest-points`),
  weeklySummary: (projectId: number) => api.post<WeeklySummary>(`/ai/projects/${projectId}/weekly-summary`),
  summarizeComments: (taskId: number) => api.post<CommentSummary>(`/ai/tasks/${taskId}/summarize-comments`),
}
