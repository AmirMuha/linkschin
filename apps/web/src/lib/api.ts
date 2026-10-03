import type { Category, SearchApiResponse, SourceStatus } from '@/types/media'
import type { SourceScopeFilter } from './urlFilters'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://127.0.0.1:8000'

export async function searchMedia(
  params: {
    q: string
    category?: Category
    refresh?: boolean
    /** Source ids to EXCLUDE from the query (the user's saved hidden set). */
    excludeSources?: string[]
    /** FR-005: 'all' opts into subscription sources; anything else is downloads-only. */
    scope?: SourceScopeFilter
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
  // Omitted for the default so a shared downloads-only URL stays as short as it was
  // before 005; a pre-005 server ignores an unknown param either way.
  if (params.scope === 'all') {
    url.searchParams.set('scope', 'all')
  }
  // `append` (not `set`) so the param repeats — the server reads a list, and it
  // can only ever drop sources, never add one (search contract, G3).
  for (const id of params.excludeSources ?? []) {
    url.searchParams.append('sources', id)
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

// --- Dynamic Catalog Feeds (User Story 1) ---

export async function fetchTrending(category: Category = 'movies', limit: number = 12): Promise<any[]> {
  try {
    const res = await fetch(`${API_BASE}/api/catalog/trending?category=${category}&limit=${limit}`, {
      headers: { Accept: 'application/json' },
      next: { revalidate: 60 },
    })
    if (!res.ok) return []
    const data = await res.json()
    return data.items || []
  } catch {
    return []
  }
}

export async function fetchLatest(category: Category = 'movies', limit: number = 14): Promise<any[]> {
  try {
    const res = await fetch(`${API_BASE}/api/catalog/latest?category=${category}&limit=${limit}`, {
      headers: { Accept: 'application/json' },
      next: { revalidate: 60 },
    })
    if (!res.ok) return []
    const data = await res.json()
    return data.items || []
  } catch {
    return []
  }
}

export async function fetchItemDetail(id: string): Promise<any | null> {
  try {
    const res = await fetch(`${API_BASE}/api/items/${encodeURIComponent(id)}`, {
      headers: { Accept: 'application/json' },
    })
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

// --- Operator Auth & Source Administration (User Story 3) ---

export async function loginOperator(username: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) {
    throw new Error('نام کاربری یا رمز عبور نامعتبر است')
  }
  const data = await res.json()
  return data.access_token
}

export async function updateSourceAddress(
  id: string,
  baseUrl?: string,
  mirrorUrl?: string,
  token?: string
): Promise<any> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_BASE}/api/sources/${id}`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify({ base_url: baseUrl, mirror_url: mirrorUrl }),
  })
  if (!res.ok) {
    throw new Error(`خطا در به‌روزرسانی آدرس منبع (${res.status})`)
  }
  return res.json()
}

export async function toggleSourceEnabled(id: string, enabled: boolean, token?: string): Promise<any> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_BASE}/api/sources/${id}/toggle`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify({ enabled }),
  })
  if (!res.ok) {
    throw new Error(`خطا در تغییر وضعیت منبع (${res.status})`)
  }
  return res.json()
}

export async function submitSourceSuggestion(data: {
  url: string
  category: string
  source_name: string
  proposed_tier?: string
  default_audio_track?: string
  contact?: string
  notes?: string
}): Promise<any> {
  const res = await fetch(`${API_BASE}/api/sources/suggest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    throw new Error(`خطا در ثبت پیشنهاد منبع (${res.status})`)
  }
  return res.json()
}

// --- YouTube to MP3 Converter (User Story 4) ---

export async function startConversion(payload: {
  url: string
  bitrate?: number
  sample_rate?: number
  write_meta?: boolean
}): Promise<{ request_id: string; status: string }> {
  const res = await fetch(`${API_BASE}/api/convert`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `خطا در شروع استخراج صوت (${res.status})`)
  }
  return res.json()
}

export async function pollConversion(requestId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/convert/${requestId}`, {
    headers: { Accept: 'application/json' },
  })
  if (!res.ok) {
    throw new Error('شناسه عملیات یافت نشد')
  }
  return res.json()
}

export async function getConversionHistory(): Promise<any[]> {
  try {
    const res = await fetch(`${API_BASE}/api/convert/history`, {
      headers: { Accept: 'application/json' },
    })
    if (!res.ok) return []
    const data = await res.json()
    return data.history || []
  } catch {
    return []
  }
}

// --- Conversational Search Assistant (User Story 5) ---

export async function sendChatMessage(
  message: string,
  sessionId?: string,
  category: Category = 'movies'
): Promise<any> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({ message, session_id: sessionId, category }),
  })
  if (!res.ok) {
    throw new Error('خطا در دریافت پاسخ دستیار')
  }
  return res.json()
}

