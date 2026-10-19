import { api } from '@/lib/api'
import type { Project } from './types'
import type {
  AddMemberInput,
  ProjectInvite,
  ProjectMember,
} from './member-types'

export const membersApi = {
  list: (projectId: number) =>
    api.get<ProjectMember[]>(`/projects/${projectId}/members`),

  add: (projectId: number, values: AddMemberInput) =>
    api.post<ProjectMember>(`/projects/${projectId}/members`, values),

  remove: (projectId: number, userId: number) =>
    api.delete<void>(`/projects/${projectId}/members/${userId}`),

  createInvite: (projectId: number) =>
    api.post<ProjectInvite>(`/projects/${projectId}/invites`),

  acceptInvite: (token: string) =>
    api.post<Project>(`/invites/${encodeURIComponent(token)}/accept`),
}