import { api } from '@/lib/api'
import type { Paginated } from '@/types/api'
import type { CreateProjectInput, Project, UpdateProjectInput } from './types'

export const projectsApi = {
  list: (page = 1) =>
    api.get<Paginated<Project>>(`/projects?page=${page}&limit=10`),

  // Sözleşme 5.2: yalnızca sistem rolü Yönetici olan oluşturabilir
  create: (values: CreateProjectInput) =>
    api.post<Project>('/projects', values),

  getDetail: (projectId: number) =>
    api.get<Project>(`/projects/${projectId}`),

  update: (projectId: number, values: UpdateProjectInput) =>
    api.patch<Project>(`/projects/${projectId}`, values),

  remove: (projectId: number) =>
    api.delete<void>(`/projects/${projectId}`),
}
