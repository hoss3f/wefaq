// frontend/src/services/api.js
import config from '../config.json'

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || config.apiBaseUrl || 'http://localhost:5000/api').replace(/\/$/, '')
const PUBLIC_BASE_URL = BASE_URL.replace(/\/api$/, '')

/** Helper to build full photo URL from relative path */
export function buildPhotoUrl(photoPath) {
  if (!photoPath) return null
  // If it's already a full URL, return as-is
  if (photoPath.startsWith('http')) return photoPath

  const normalizedPath = photoPath.startsWith('/') ? photoPath : `/${photoPath}`
  return `${PUBLIC_BASE_URL}${normalizedPath}`
}

/** Attach admin/user credentials stored after login. */
function buildAuthHeaders() {
  const headers = {}

  try {
    const adminRaw = localStorage.getItem('wefaq_admin')
    if (adminRaw) {
      const admin = JSON.parse(adminRaw)
      if (admin?.id != null) {
        headers['X-Admin-Id'] = String(admin.id)
      }
    }
  } catch {
    // ignore malformed session data
  }

  try {
    const userRaw = localStorage.getItem('wefaq_user')
    if (userRaw) {
      const user = JSON.parse(userRaw)
      if (user?.code) {
        headers['X-User-Code'] = user.code
      }
    }
  } catch {
    // ignore malformed session data
  }

  return headers
}

/**
 * دالة موحدة لإرسال الطلبات إلى الخادم الخلفي، وتحويل الاستجابة والأخطاء بشكل متسق
 */
async function request(path, { method = 'GET', body } = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...buildAuthHeaders()
    },
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    const fallback = response.status >= 500
      ? 'حدث خطأ في الخادم، تأكد من تشغيله وحاول مرة أخرى'
      : 'حدث خطأ في الاتصال بالخادم'
    throw new Error(data.message || fallback)
  }

  return data
}

export const apiGet = (path) => request(path, { method: 'GET' })
export const apiPost = (path, body) => request(path, { method: 'POST', body })
export const apiPut = (path, body) => request(path, { method: 'PUT', body })
export const apiDelete = (path, body) => request(path, { method: 'DELETE', body })

/** POST multipart/form-data (do not set Content-Type — browser sets boundary). */
export async function apiPostForm(path, formData) {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      ...buildAuthHeaders()
    },
    body: formData
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    const fallback = response.status >= 500
      ? 'حدث خطأ في الخادم، تأكد من تشغيله وحاول مرة أخرى'
      : 'حدث خطأ في الاتصال بالخادم'
    throw new Error(data.message || fallback)
  }

  return data
}
