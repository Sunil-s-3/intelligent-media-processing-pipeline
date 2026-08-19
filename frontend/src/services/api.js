// In development, leave BASE_URL empty so requests go to the same origin
// (http://localhost:5173 or 5174) and the Vite proxy forwards /api → backend.
// In production builds, set VITE_API_BASE_URL to the real backend origin.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, options)
  const data = await res.json().catch(() => null)

  if (!res.ok) {
    const message =
      data?.message || data?.error || `HTTP ${res.status}`
    const err = new Error(message)
    err.status = res.status
    err.data = data
    throw err
  }

  return { status: res.status, data }
}

export async function checkHealth() {
  return request('/api/v1/health')
}

export async function uploadImage(file) {
  const form = new FormData()
  form.append('image', file)
  return request('/api/v1/images', { method: 'POST', body: form })
}

export async function getStatus(processingId) {
  return request(`/api/v1/images/${processingId}/status`)
}

export async function getResults(processingId) {
  return request(`/api/v1/images/${processingId}/results`)
}
