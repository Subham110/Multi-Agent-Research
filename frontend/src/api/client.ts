const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(`${API_URL}${path}`, { ...options, headers })
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const data = (await response.json()) as { detail?: string }
      message = data.detail ?? message
    } catch {
      // Keep the fallback message for non-JSON errors.
    }
    throw new ApiError(response.status, message)
  }
  return response.json() as Promise<T>
}

export { API_URL }
