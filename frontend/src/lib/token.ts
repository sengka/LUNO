// JWT erişim token'ı tarayıcıda saklanır, sayfa yenilense de oturum kalır.
const TOKEN_KEY = 'luno_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}
