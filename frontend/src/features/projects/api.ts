import { api } from '@/lib/api'
import type { Project, UpdateProjectInput } from './types'

export const projectsApi = {
  getDetail: (projectId: number) =>
    api.get<Project>(`/projects/${projectId}`),

  update: (projectId: number, values: UpdateProjectInput) =>
    api.patch<Project>(`/projects/${projectId}`, values),
}