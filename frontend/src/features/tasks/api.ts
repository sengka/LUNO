import { api } from '@/lib/api'
import type { Task, UpdateTaskInput } from './types'

export const taskKeys = {
  all: ['tasks'] as const,
  detail: (id: number) => ['tasks', 'detail', id] as const,
}

export const tasksApi = {
  getDetail: (id: number) => api.get<Task>(`/tasks/${id}`),
  update: (id: number, input: UpdateTaskInput) => api.patch<Task>(`/tasks/${id}`, input),
  remove: (id: number) => api.delete<void>(`/tasks/${id}`),
}
