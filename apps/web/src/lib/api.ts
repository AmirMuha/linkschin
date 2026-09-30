import type { Category, SearchApiResponse, SourceStatus } from '@/types/media'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://127.0.0.1:8000'

export async function searchMedia(
  params: {
    q: string
    category?: Category
    refresh?: boolean
  },
  signal?: AbortSignal
): Promise<SearchApiResponse> {
  const url = new URL(`${API_BASE}/api/search`)
  url.searchParams.set('q', params.q)
  if (params.category) {
    url.searchParams.set('category', params.category)
  }
  if (params.refresh) {
    url.searchParams.set('refresh', 'true')
  }

  const response = await fetch(url.toString(), {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
    signal,
  })

  if (!response.ok) {
    let errorDetail = `خطا در برقراری ارتباط با سرور (${response.status})`
    try {
      const errJson = await response.json()
      if (errJson?.detail) {
        errorDetail = errJson.detail
      }
    } catch {
      // Ignore JSON parse errors on non-200 responses
    }
    throw new Error(errorDetail)
  }

  return response.json()
}

export async function fetchSources(signal?: AbortSignal): Promise<SourceStatus[]> {
  const response = await fetch(`${API_BASE}/api/sources`, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
    signal,
  })

  if (!response.ok) {
    throw new Error(`خطا در دریافت لیست منابع (${response.status})`)
  }

  return response.json()
}
