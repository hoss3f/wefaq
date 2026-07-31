// frontend/src/services/userService.js
import { apiGet, apiPost, apiPut, apiPostForm } from './api'

/** جلب أسئلة الاختيار من متعدد والأسئلة المفتوحة لعرضها في النموذج */
export function getQuestions() {
  return apiGet('/questions')
}

/** تسجيل مستخدم جديد بالبيانات الشخصية */
export function registerUser(personalData, photoFile) {
  const formData = new FormData()
  Object.entries(personalData).forEach(([key, value]) => {
    if (value != null && value !== '') {
      formData.append(key, value)
    }
  })
  if (photoFile) {
    formData.append('photo', photoFile)
  }
  return apiPostForm('/users/register', formData)
}

/** حفظ إجابات المستخدم على الأسئلة المغلقة والمفتوحة */
export function saveAnswers(userId, mcqAnswers, openAnswers) {
  return apiPost(`/users/${userId}/answers`, { mcq: mcqAnswers, open: openAnswers })
}

/** إكمال طلب مستخدم بالكود (بيانات + إجابات) في طلب واحد */
export function completeApplication(userId, personal, mcqAnswers, openAnswers) {
  return apiPost(`/users/${userId}/complete`, {
    personal,
    mcq: mcqAnswers,
    open: openAnswers
  })
}

/** جلب بيانات مستخدم معيّن مع إجاباته */
export function getUser(userId) {
  return apiGet(`/users/${userId}`)
}

/** تحديث البيانات الشخصية للمستخدم */
export function updateUser(userId, personalData) {
  return apiPut(`/users/${userId}`, personalData)
}

/** جلب إشعارات مستخدم معيّن */
export function getUserNotifications(userId) {
  return apiGet(`/notifications/user/${userId}`)
}
