// frontend/src/services/api.js
import config from '../config.json'

const BASE_URL = config.apiBaseUrl

function buildAuthHeaders() {
  const headers = { 'Content-Type': 'application/json' }
  try {
    const userRaw = localStorage.getItem('wefaq_user')
    if (userRaw) {
      const user = JSON.parse(userRaw)
      if (user?.code) headers['X-User-Code'] = user.code
    }
    const adminRaw = localStorage.getItem('wefaq_admin')
    if (adminRaw) {
      const admin = JSON.parse(adminRaw)
      if (admin?.id) headers['X-Admin-Id'] = String(admin.id)
    }
  } catch {
    // ignore malformed localStorage
  }
  return headers
}

/**
 * دالة موحدة لإرسال الطلبات إلى الخادم الخلفي، وتحويل الاستجابة والأخطاء بشكل متسق
 */
async function request(path, { method = 'GET', body } = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: buildAuthHeaders(),
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
