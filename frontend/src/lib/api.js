const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || 'Request failed')
  }

  return response.json()
}

export const api = {
  // Health check
  healthCheck: () => request('/api/v1/health'),

  // Persons
  searchPersons: (query, limit = 20) =>
    request(`/api/v1/persons/search?q=${encodeURIComponent(query)}&limit=${limit}`),

  getPerson: (id) => request(`/api/v1/persons/${id}`),

  listPersons: (limit = 50, offset = 0) =>
    request(`/api/v1/persons?limit=${limit}&offset=${offset}`),

  getFoundingAncestors: (limit = 12) =>
    request(`/api/v1/persons/founding-ancestors?limit=${limit}`),

  // Families
  getAncestors: (personId, generations = 3) =>
    request(`/api/v1/families/${personId}/ancestors?generations=${generations}`),

  getDescendants: (personId, generations = 3) =>
    request(`/api/v1/families/${personId}/descendants?generations=${generations}`),
}
