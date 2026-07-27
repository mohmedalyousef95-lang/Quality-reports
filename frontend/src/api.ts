const BASE = ''

class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    headers:
      options.body && !(options.body instanceof FormData)
        ? { 'Content-Type': 'application/json', ...options.headers }
        : options.headers,
    ...options,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      detail = data.detail || detail
    } catch {
      // ignore
    }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  const contentType = res.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return res.json()
  }
  return undefined as T
}

export const api = {
  login: (password: string) =>
    request<{ ok: boolean }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ password }),
    }),
  logout: () => request<{ ok: boolean }>('/api/auth/logout', { method: 'POST' }),
  authStatus: () => request<{ authenticated: boolean }>('/api/auth/status'),

  searchSchools: (q: string, limit = 20) =>
    request<School[]>(`/api/schools?q=${encodeURIComponent(q)}&limit=${limit}`),
  nearbySchools: (lat: number, lng: number, limit = 15) =>
    request<School[]>(`/api/schools/nearby?lat=${lat}&lng=${lng}&limit=${limit}`),
  getSchool: (id: string) => request<School>(`/api/schools/${id}`),
  getSchoolReports: (id: string) => request<ReportListItem[]>(`/api/schools/${id}/reports`),

  getChecklist: (category: string) =>
    request<ChecklistItem[]>(`/api/checklist?category=${category}`),
  addChecklistItem: (category: string, label: string) =>
    request<ChecklistItem>('/api/checklist', {
      method: 'POST',
      body: JSON.stringify({ category, label }),
    }),
  deleteChecklistItem: (id: number) =>
    request<{ ok: boolean }>(`/api/checklist/${id}`, { method: 'DELETE' }),
  getNoteSuggestions: () => request<NoteSuggestion[]>('/api/checklist/note-suggestions'),

  createReport: (payload: {
    school_id: string
    visit_date: string
    visitor_name: string
    contractor?: string
  }) => request<Report>('/api/reports', { method: 'POST', body: JSON.stringify(payload) }),
  getReport: (id: number) => request<Report>(`/api/reports/${id}`),
  deleteReport: (id: number) => request<{ ok: boolean }>(`/api/reports/${id}`, { method: 'DELETE' }),

  uploadPhoto: (reportId: number, category: string, file: File) => {
    const form = new FormData()
    form.append('category', category)
    form.append('file', file)
    return request<ReportPhoto & { url: string }>(`/api/reports/${reportId}/photos`, {
      method: 'POST',
      body: form,
    })
  },
  deletePhoto: (reportId: number, photoId: number) =>
    request<{ ok: boolean }>(`/api/reports/${reportId}/photos/${photoId}`, { method: 'DELETE' }),
  updateCaption: (reportId: number, photoId: number, caption: string) =>
    request<{ ok: boolean }>(`/api/reports/${reportId}/photos/${photoId}/caption`, {
      method: 'PUT',
      body: JSON.stringify({ caption }),
    }),

  listReports: (params: {
    search?: string
    status?: string
    zone?: string
    engineer?: string
    supervisor?: string
    sort?: string
  }) => {
    const qs = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v) qs.set(k, v)
    })
    return request<ReportRow[]>(`/api/reports?${qs.toString()}`)
  },
  getReportFilters: () => request<FilterOptions>('/api/reports/filters'),

  replaceNotes: (reportId: number, category: string, notes: NoteInput[]) =>
    request<{ ok: boolean }>(`/api/reports/${reportId}/notes`, {
      method: 'PUT',
      body: JSON.stringify({ category, notes }),
    }),

  updateReportInfo: (reportId: number, info: ReportInfo) =>
    request<Report>(`/api/reports/${reportId}/info`, {
      method: 'PUT',
      body: JSON.stringify(info),
    }),

  downloadUrl: (reportId: number) => `/api/reports/${reportId}/download`,

  // Fetch the generated PPTX as a blob and trigger a save. Using fetch (not a
  // link navigation) avoids the PWA service worker intercepting the request.
  downloadReport: async (reportId: number, filename: string) => {
    const res = await fetch(`/api/reports/${reportId}/download`, {
      credentials: 'include',
    })
    if (!res.ok) throw new Error(`download failed (${res.status})`)
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  },
}

export type School = {
  ministry_number: string
  name: string
  region?: string
  address?: string
  zone?: string
  engineer?: string
  supervisor?: string
  lat?: number
  lng?: number
  building_type?: string
  national_address?: string
  ownership_type?: string
}

export type ChecklistItem = {
  id: number
  category: string
  label: string
  position: number
}

export type NoteSuggestion = {
  id: number
  category: string
  item: string
  text: string
  position: number
}

export type ReportPhoto = {
  id: number
  category: string
  position: number
  file_path: string
  caption?: string
}

export type ReportNote = {
  id: number
  category: string
  item: string
  note: string
  status: string
  position: number
}

export type NoteInput = {
  category: string
  item: string
  note: string
  status: string
  position: number
}

export type ReportInfo = {
  contractor: string
  visit_type: string
  during_readiness_plan: string
  team_count: number | null
  oversight_supervisor_present: string
  team_types: string
  important_notes: string
}

export type Report = ReportInfo & {
  id: number
  school_id: string
  visit_date: string
  visitor_name?: string
  created_at: string
  status?: string
  photos: ReportPhoto[]
  notes: ReportNote[]
}

export type ReportListItem = {
  id: number
  school_id: string
  visit_date: string
  visitor_name?: string
  created_at: string
  status?: string
}

export type ReportRow = {
  id: number
  school_id: string
  school_name: string
  zone?: string
  engineer?: string
  supervisor?: string
  visit_date: string
  visitor_name?: string
  status: string
  photo_count: number
  note_count: number
  completion: number
  created_at: string
}

export type FilterOptions = {
  zones: string[]
  engineers: string[]
  supervisors: string[]
}
