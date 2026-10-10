import { api } from '@/lib/api'
import type { Paginated, Role, User } from '@/types/api'

export interface ListUsersParams {
  search?: string
  page?: number
  limit?: number
}

// Sözleşme 4.1 ve 4.2 (v1.1: search, page, limit)
export const usersApi = {
  list: ({ search, page = 1, limit = 10 }: ListUsersParams) => {
    const params = new URLSearchParams({ page: String(page), limit: String(limit) })
    if (search) params.set('search', search)
    return api.get<Paginated<User>>(`/users?${params}`)
  },
  updateRole: (userId: number, role: Role) => api.patch<User>(`/users/${userId}/role`, { role }),
}
