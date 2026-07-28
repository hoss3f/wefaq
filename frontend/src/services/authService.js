// frontend/src/services/authService.js
import { apiPost } from './api'

/** تسجيل دخول المستخدم عبر الكود الخاص به */
export function loginUser(code) {
  return apiPost('/auth/user-login', { code })
}

/** تسجيل دخول الإداري عبر البريد الإلكتروني وكلمة المرور */
export function loginAdmin(email, password) {
  return apiPost('/auth/admin-login', { email, password })
}
