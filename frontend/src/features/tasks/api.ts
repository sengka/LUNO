import { api } from '@/lib/api'
import type { Paginated } from '@/types/api'
import type { CreateLabelInput, CreateSubtaskInput, Label, Task, UpdateTaskInput } from './types'

export const taskKeys = {
  all: ['tasks'] as const,
  detail: (id: number) => ['tasks', 'detail', id] as const,
  subtasks: (id: number, page: number) => ['tasks', 'subtasks', id, page] as const,
  labels: (projectId: number) => ['projects', 'labels', projectId] as const,
}

export const tasksApi = {
  getDetail: (id: number) => api.get<Task>(`/tasks/${id}`),
  update: (id: number, input: UpdateTaskInput) => api.patch<Task>(`/tasks/${id}`, input),
  remove: (id: number) => api.delete<void>(`/tasks/${id}`),
  listSubtasks: (projectId: number, parentId: number, page: number) =>
    api.get<Paginated<Task>>(`/projects/${projectId}/tasks?parent_id=${parentId}&include_pending=true&page=${page}&limit=10`),
  createSubtask: (parentId: number, input: CreateSubtaskInput) =>
    api.post<Task>(`/tasks/${parentId}/subtasks`, input),
  listLabels: (projectId: number) => api.get<Label[]>(`/projects/${projectId}/labels`),
  createLabel: (projectId: number, input: CreateLabelInput) =>
    api.post<Label>(`/projects/${projectId}/labels`, input),
}
