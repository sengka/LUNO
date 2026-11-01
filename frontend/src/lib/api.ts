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

const networkError = () =>
  new ApiError(0, {
    code: 'NETWORK_ERROR',
    message: 'Sunucuya ulaşılamadı. İnternet bağlantını kontrol et.',
    fields: null,
    details: null,
  })

// Başarısız yanıtı sözleşmedeki hata biçimine çevirir (normal istek, yükleme ve indirme için ortak)
function toApiError(status: number, data: unknown, hadToken: boolean) {
  // Token'lı bir istek 401 aldıysa oturum bitmiştir. Girişteki 401 (hatalı şifre) bu değil.
  if (status === 401 && hadToken) onUnauthorized?.()

  const error = (data as ApiErrorBody | null)?.error
  return new ApiError(
    status,
    error ?? {
      code: 'INTERNAL_ERROR',
      message: 'Beklenmeyen bir hata oluştu.',
      fields: null,
      details: null,
    },
  )
}

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request<T>(method: Method, path: string, body?: unknown): Promise<T> {
  const headers = authHeaders()
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw networkError()
  }

  if (response.status === 204) return undefined as T

  const data = await response.json().catch(() => null)
  if (!response.ok) throw toApiError(response.status, data, 'Authorization' in headers)
  return data as T
}

// multipart/form-data yükleme. fetch yükleme ilerlemesini vermediği için XMLHttpRequest kullanılır.
function upload<T>(path: string, formData: FormData, onProgress?: (percent: number) => void): Promise<T> {
  const headers = authHeaders()

  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_URL}${path}`)
    for (const [name, value] of Object.entries(headers)) xhr.setRequestHeader(name, value)

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(Math.round((event.loaded / event.total) * 100))
    }
    xhr.onerror = () => reject(networkError())
    xhr.onload = () => {
      let data: unknown = null
      try {
        data = xhr.responseText ? JSON.parse(xhr.responseText) : null
      } catch {
        data = null
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(data as T)
      else reject(toApiError(xhr.status, data, 'Authorization' in headers))
    }

    xhr.send(formData)
  })
}

// Content-Disposition: attachment; filename="..."; filename*=UTF-8''...
function filenameFromHeader(header: string | null) {
  if (!header) return null
  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(header)
  if (encoded) return decodeURIComponent(encoded[1])
  const plain = /filename="?([^";]+)"?/i.exec(header)
  return plain ? plain[1] : null
}

// Token gerektiren dosyayı indirip tarayıcıya kaydettirir (düz bağlantı Authorization başlığı gönderemez)
async function download(path: string, fallbackName: string) {
  const headers = authHeaders()

  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, { headers })
  } catch {
    throw networkError()
  }
  if (!response.ok) {
    const data = await response.json().catch(() => null)
    throw toApiError(response.status, data, 'Authorization' in headers)
  }

  // Başlık CORS ile açılmadıysa okunamaz; o zaman listedeki dosya adı kullanılır
  const name = filenameFromHeader(response.headers.get('Content-Disposition')) ?? fallbackName
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = name
  document.body.append(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, body),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
  delete: <T>(path: string) => request<T>('DELETE', path),
  upload,
  download,
}
