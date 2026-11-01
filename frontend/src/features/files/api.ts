import { api } from '@/lib/api'
import type { Paginated } from '@/types/api'
import type { ProjectFile } from './types'

export const fileKeys = {
  task: (taskId: number) => ['files', 'task', taskId] as const,
}

// Sözleşme 8.1 – 8.4
export const filesApi = {
  listForTask: (projectId: number, taskId: number) =>
    api.get<Paginated<ProjectFile>>(`/projects/${projectId}/files?task_id=${taskId}&page=1&limit=100`),

  upload: (projectId: number, file: File, taskId: number | null, onProgress?: (percent: number) => void) => {
    const form = new FormData()
    form.append('file', file)
    if (taskId !== null) form.append('task_id', String(taskId))
    return api.upload<ProjectFile>(`/projects/${projectId}/files`, form, onProgress)
  },

  download: (file: ProjectFile) => api.download(`/files/${file.id}/download`, file.name),

  remove: (fileId: number) => api.delete<void>(`/files/${fileId}`),
}
