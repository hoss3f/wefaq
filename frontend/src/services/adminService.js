// frontend/src/services/adminService.js
import { apiGet, apiPost, apiPut, apiDelete } from './api'

/** جلب قائمة المستخدمين مع تصفية اختيارية */
export function listUsers({
  status,
  scope,
  requestingAdminId,
  assignedAdminId,
  education,
  financial
} = {}) {
  const params = new URLSearchParams()
  if (status) params.set('status', status)
  if (scope) params.set('scope', scope)
  if (requestingAdminId) params.set('requesting_admin_id', requestingAdminId)
  if (assignedAdminId) params.set('assigned_admin_id', assignedAdminId)
  if (education) params.set('education', education)
  if (financial) params.set('financial', financial)
  const query = params.toString()
  return apiGet(`/admin/users${query ? `?${query}` : ''}`)
}

/** تحديث حالة طلب مستخدم مع سبب اختياري */
export function updateUserStatus(userId, status, adminId, statusReason = '') {
  return apiPut(`/admin/users/${userId}/status`, {
    status,
    status_reason: statusReason,
    admin_id: adminId
  })
}

/** تعيين أو إعادة تعيين مسؤول الحالة */
export function assignUserCase(userId, currentAdminId, targetAdminId) {
  return apiPut(`/admin/users/${userId}/assign`, {
    admin_id: currentAdminId,
    target_admin_id: targetAdminId
  })
}

/** جلب سجل الإجراءات */
export function getActivityLogs({ adminId, filterAdminId, userId, dateFrom, dateTo } = {}) {
  const params = new URLSearchParams()
  if (adminId) params.set('admin_id', adminId)
  if (filterAdminId) params.set('filter_admin_id', filterAdminId)
  if (userId) params.set('user_id', userId)
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  const query = params.toString()
  return apiGet(`/admin/logs${query ? `?${query}` : ''}`)
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
export function generateUserCode(fullName, adminId) {
  return apiPost('/admin/users/generate-code', {
    full_name: fullName || '',
    admin_id: adminId
  })
}

/** جلب قائمة الإداريين */
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
