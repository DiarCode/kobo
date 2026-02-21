import ky from 'ky'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export const apiClient = ky.create({
  prefixUrl: API_BASE_URL,
  credentials: 'include',
})
