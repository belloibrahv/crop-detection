const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export class ApiError extends Error {
  status: number
  code?: string

  constructor(message: string, status: number, code?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

export async function apiFetch(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  const url = `${API_BASE_URL}${endpoint}`
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  if (!response.ok) {
    let errorMessage = 'An error occurred'
    let errorCode: string | undefined

    try {
      const data = await response.json()
      errorMessage = data.message || data.error || errorMessage
      errorCode = data.code
    } catch {
      errorMessage = response.statusText || errorMessage
    }

    throw new ApiError(errorMessage, response.status, errorCode)
  }

  return response
}

export async function apiGet<T>(endpoint: string): Promise<T> {
  const response = await apiFetch(endpoint, { method: 'GET' })
  return response.json()
}

export async function apiPost<T>(endpoint: string, body: unknown): Promise<T> {
  const response = await apiFetch(endpoint, {
    method: 'POST',
    body: JSON.stringify(body),
  })
  return response.json()
}

export async function apiPut<T>(endpoint: string, body: unknown): Promise<T> {
  const response = await apiFetch(endpoint, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
  return response.json()
}

export async function apiDelete(endpoint: string): Promise<void> {
  await apiFetch(endpoint, { method: 'DELETE' })
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'An unexpected error occurred'
}
