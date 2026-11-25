import { api } from '@/lib/api'
import type { PointsSuggestion } from './types'

// Sözleşme 13: LLM uç noktaları yalnızca öneri döndürür, hiçbir şey kaydetmez.
// Kullanıcı onaylarsa normal uç noktalar (ör. görev güncelleme) çağrılır.
export const aiApi = {
  suggestPoints: (taskId: number) => api.post<PointsSuggestion>(`/ai/tasks/${taskId}/suggest-points`),
}
