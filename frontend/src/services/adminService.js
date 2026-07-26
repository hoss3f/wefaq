// frontend/src/services/adminService.js
import { apiGet, apiPost, apiPut, apiDelete } from './api'

/** جلب قائمة المستخدمين، مع إمكانية التصفية حسب الحالة */
export function listUsers(status) {
  const query = status ? `?status=${status}` : ''
  return apiGet(`/admin/users${query}`)
}

/** تحديث حالة طلب مستخدم مع سبب اختياري */
export function updateUserStatus(userId, status, statusReason = '') {
  return apiPut(`/admin/users/${userId}/status`, { status, status_reason: statusReason })
}

/** إضافة ملاحظة إداري على مستخدم معيّن */
export function addNote(userId, adminId, noteText, isVisibleToUser = false) {
  return apiPost(`/admin/users/${userId}/notes`, {
    admin_id: adminId,
    note_text: noteText,
    is_visible_to_user: isVisibleToUser
  })
}

/** جلب ملاحظات مستخدم معيّن */
export function getNotes(userId) {
  return apiGet(`/admin/users/${userId}/notes`)
}

/** توليد كود مستخدم جديد (الاسم اختياري) */
export function generateUserCode(fullName) {
  return apiPost('/admin/users/generate-code', { full_name: fullName || '' })
}

/** جلب قائمة الإداريين (المدير العام فقط) */
export function listAdmins(adminId) {
  return apiGet(`/admin/admins?admin_id=${adminId}`)
}

/** حذف مستخدم (المدير العام فقط) */
export function deleteUser(userId, adminId) {
  return apiDelete(`/admin/users/${userId}`, { admin_id: adminId })
}

/** حذف إداري (المدير العام فقط) */
export function deleteAdmin(targetId, adminId) {
  return apiDelete(`/admin/admins/${targetId}`, { admin_id: adminId })
}

/** إنشاء حساب إداري جديد */
export function createAdmin(adminData) {
  return apiPost('/admin/create', adminData)
}
