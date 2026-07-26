// frontend/src/services/api.js
import config from '../config.json'

const BASE_URL = config.apiBaseUrl

/**
 * دالة موحدة لإرسال الطلبات إلى الخادم الخلفي، وتحويل الاستجابة والأخطاء بشكل متسق
 */
async function request(path, { method = 'GET', body } = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(data.message || 'حدث خطأ في الاتصال بالخادم')
  }

  return data
}

export const apiGet = (path) => request(path, { method: 'GET' })
export const apiPost = (path, body) => request(path, { method: 'POST', body })
export const apiPut = (path, body) => request(path, { method: 'PUT', body })
export const apiDelete = (path, body) => request(path, { method: 'DELETE', body })
