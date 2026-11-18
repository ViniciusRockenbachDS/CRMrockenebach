import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'

import type { ApiErrorBody, TokenPair } from '@/types/api'

export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

const ACCESS_KEY = 'crm.access_token'
const REFRESH_KEY = 'crm.refresh_token'

export const tokenStorage = {
  getAccess: () => localStorage.getItem(ACCESS_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  set: (tokens: TokenPair) => {
    localStorage.setItem(ACCESS_KEY, tokens.access_token)
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token)
  },
  clear: () => {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

/** Evento disparado quando a sessão expira de vez (o AuthContext escuta e redireciona ao login). */
export const LOGOUT_EVENT = 'crm:logout'

export const http = axios.create({
  baseURL: API_URL,
  timeout: 30_000,
  // FastAPI espera listas como ?status=a&status=b (sem colchetes).
  paramsSerializer: { indexes: null },
})

http.interceptors.request.use((config) => {
  const token = tokenStorage.getAccess()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Renovação automática do access token: várias requisições 401 simultâneas
// compartilham a mesma chamada de refresh.
let refreshPromise: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  const refresh = tokenStorage.getRefresh()
  if (!refresh) throw new Error('Sem refresh token')
  const { data } = await axios.post<TokenPair>(`${API_URL}/auth/refresh`, { refresh_token: refresh })
  tokenStorage.set(data)
  return data.access_token
}

http.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined
    const isAuthRoute = original?.url?.includes('/auth/login') || original?.url?.includes('/auth/refresh')

    if (error.response?.status === 401 && original && !original._retry && !isAuthRoute) {
      original._retry = true
      try {
        refreshPromise ??= refreshAccessToken().finally(() => {
          refreshPromise = null
        })
        const token = await refreshPromise
        original.headers.Authorization = `Bearer ${token}`
        return http(original)
      } catch {
        tokenStorage.clear()
        window.dispatchEvent(new Event(LOGOUT_EVENT))
      }
    }
    return Promise.reject(error)
  },
)

/** Mensagem amigável a partir de qualquer erro (formato padrão da API: {code, message, details}). */
export function getErrorMessage(error: unknown, fallback = 'Algo deu errado. Tente novamente.'): string {
  if (axios.isAxiosError(error)) {
    const body = error.response?.data as ApiErrorBody | undefined
    if (body?.details?.length) {
      const first = body.details[0]
      return first.field ? `${first.field}: ${first.message}` : first.message
    }
    if (body?.message) return body.message
    if (error.code === 'ERR_NETWORK') return 'Não foi possível conectar à API. Verifique se o backend está rodando.'
  }
  return fallback
}

/** Remove parâmetros vazios ('' / undefined / null / []) antes de enviar como query string. */
export function cleanParams<T extends object>(params: T): Partial<T> {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => {
      if (value === undefined || value === null || value === '') return false
      if (Array.isArray(value) && value.length === 0) return false
      return true
    }),
  ) as Partial<T>
}
