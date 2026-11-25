import type { StoryPoints } from '@/features/tasks/types'

// Sözleşme 13.1: yanıtlarda hangi servisin kullanıldığı döner
export type LLMProvider = 'groq' | 'gemini'

export const PROVIDER_LABELS: Record<LLMProvider, string> = {
  groq: 'Groq',
  gemini: 'Gemini',
}

// Sözleşme 13.4
export interface PointsSuggestion {
  provider: LLMProvider
  story_points: StoryPoints
  reason: string
}

// Sözleşme 13.5
export interface WeeklySummary {
  provider: LLMProvider
  from: string
  to: string
  summary: string
}

// Sözleşme 13.6
export interface CommentSummary {
  provider: LLMProvider
  decisions: string[]
  open_questions: string[]
  summary: string
}
