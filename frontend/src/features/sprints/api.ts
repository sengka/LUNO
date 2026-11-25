import { api } from '@/lib/api'
import type { Task } from '@/features/tasks/types'
import type { Paginated } from '@/types/api'
import type { CreateSprintInput, Sprint, SprintTasksAddResponse } from './types'

export const sprintKeys = {
  // ActiveSprintProgress ile aynı anahtar: sprinte görev eklenince ilerleme kartı da güncellenir
  list: (projectId: number) => ['tasks', 'sprints', projectId] as const,
  tasks: (sprintId: number) => ['tasks', 'sprint-tasks', sprintId] as const,
  backlog: (projectId: number) => ['tasks', 'backlog', projectId] as const,
}

// Sözleşme 11.1 – 11.3
export const sprintsApi = {
  list: (projectId: number) => api.get<Sprint[]>(`/projects/${projectId}/sprints`),
  create: (projectId: number, input: CreateSprintInput) => api.post<Sprint>(`/projects/${projectId}/sprints`, input),
  addTasks: (sprintId: number, taskIds: number[]) =>
    api.post<SprintTasksAddResponse>(`/sprints/${sprintId}/tasks`, { task_ids: taskIds }),
  removeTask: (sprintId: number, taskId: number) => api.delete<void>(`/sprints/${sprintId}/tasks/${taskId}`),
  tasksOf: (projectId: number, sprintId: number) =>
    api.get<Paginated<Task>>(`/projects/${projectId}/tasks?sprint_id=${sprintId}&page=1&limit=100`),
  // Backlog: tamamlanmamış ana görevler; sprinte atanmamış olanlar istemcide ayrılır
  // (sözleşmede "sprinti olmayan" filtresi yok)
  openTasks: (projectId: number) =>
    api.get<Paginated<Task>>(`/projects/${projectId}/tasks?status=TODO,IN_PROGRESS,REVIEW_TESTING&page=1&limit=100`),
}
