import type { ApiErrorBody } from '@/types/api'
import { getToken } from '@/lib/token'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

// Backend'in ortak hata formatını (sözleşme 1.5) taşıyan hata sınıfı
export class ApiError extends Error {
  status: number
  code: string
  fields: Record<string, string> | null
  details: unknown

  constructor(status: number, body: ApiErrorBody['error']) {
    super(body.message)
    this.status = status
    this.code = body.code
    this.fields = body.fields
    this.details = body.details
  }
}

// Oturum düşünce (401) ne yapılacağını AuthProvider belirler
let onUnauthorized: (() => void) | null = null

export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler
}

type Method = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'

async function request<T>(method: Method, path: string, body?: unknown): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`

  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(0, {
      code: 'NETWORK_ERROR',
      message: 'Sunucuya ulaşılamadı. İnternet bağlantını kontrol et.',
      fields: null,
      details: null,
    })
  }

  if (response.status === 204) return undefined as T

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    // Token'lı bir istek 401 aldıysa oturum bitmiştir. Girişteki 401 (hatalı şifre) bu değil.
    if (response.status === 401 && token) onUnauthorized?.()

    const error = (data as ApiErrorBody | null)?.error
    throw new ApiError(
      response.status,
      error ?? {
        code: 'INTERNAL_ERROR',
        message: 'Beklenmeyen bir hata oluştu.',
        fields: null,
        details: null,
      },
    )
  }

  return data as T
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, body),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
  delete: <T>(path: string) => request<T>('DELETE', path),
}
