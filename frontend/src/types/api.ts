// API sözleşmesindeki (docs/api/api-sozlesmesi.md) veri nesneleri

export type Role = 'YONETICI' | 'EKIP_UYESI'

export type Theme = 'LIGHT' | 'DARK'

export interface User {
  id: number
  full_name: string
  email: string
  role: Role
  avatar_url: string | null
  theme: Theme
  created_at: string
}

export interface LoginResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  user: User
}

// Sözleşme v1.1: liste uç noktaları { items, total, page, limit } döner
export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  limit: number
}

export interface ApiErrorBody {
  error: {
    code: string
    message: string
    fields: Record<string, string> | null
    details: unknown
  }
}

export const ROLE_LABELS: Record<Role, string> = {
  YONETICI: 'Yönetici',
  EKIP_UYESI: 'Ekip Üyesi',
}
