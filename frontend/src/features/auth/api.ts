import { api } from '@/lib/api'
import type { LoginResponse, User } from '@/types/api'

export interface RegisterInput {
  full_name: string
  email: string
  password: string
}

export interface LoginInput {
  email: string
  password: string
}

// Sözleşme 3.1 – 3.4
export const authApi = {
  register: (input: RegisterInput) => api.post<User>('/auth/register', input),
  login: (input: LoginInput) => api.post<LoginResponse>('/auth/login', input),
  logout: () => api.post<void>('/auth/logout'),
  me: () => api.get<User>('/auth/me'),
}
