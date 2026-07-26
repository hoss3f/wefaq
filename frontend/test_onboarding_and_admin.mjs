// frontend/test_onboarding_and_admin.mjs
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const config = JSON.parse(readFileSync(new URL('./src/config.json', import.meta.url)))
const BASE = config.apiBaseUrl
const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')
const ADMINS_JSON = join(ROOT, 'backend', 'data', 'admins.json')

async function call(path, method = 'GET', body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined
  })
  const data = await res.json()
  return { status: res.status, data }
}

function assert(condition, message) {
  if (!condition) throw new Error(`فشل الاختبار: ${message}`)
  console.log('OK:', message)
}

function readAdminsFile() {
  return JSON.parse(readFileSync(ADMINS_JSON, 'utf-8'))
}

async function run() {
  console.log('بدء اختبار مسار أول دخول + مزامنة الإداريين + متتبع الخطوات...\n')

  // 1) توليد كود بدون اسم → متقدم جديد
  const genEmpty = await call('/admin/users/generate-code', 'POST', {})
  assert(genEmpty.status === 201, 'توليد كود بدون اسم')
  assert(genEmpty.data.user.full_name === 'متقدم جديد', 'الاسم الافتراضي متقدم جديد')
  const codeUserId = genEmpty.data.user.id
  const code = genEmpty.data.user.code

  // 2) أول دخول بالكود → needs_onboarding
  const login1 = await call('/auth/user-login', 'POST', { code })
  assert(login1.data.success, 'دخول بالكود المولد')
  assert(login1.data.user.needs_onboarding === true, 'needs_onboarding=true لأول مرة')

  // 3) إكمال الطلب: بيانات ثم أسئلة
  const complete = await call(`/users/${codeUserId}/complete`, 'POST', {
    personal: {
      full_name: 'سارة أحمد',
      phone: '0555000111',
      email: 'sara.onboard@wefaq.com',
      birthday: '1999-03-20',
      gender: 'أنثى',
      country: 'قطر'
    },
    mcq: { q1: 'بكالوريوس', q2: 'متوسط', q3: 'لا', q4: 'الأخلاق' },
    open: { q1: 'هادئة وصادقة', q2: 'احترام وتفاهم', q3: 'بيت مستقر', q4: 'لا' }
  })
  assert(complete.status === 200, 'إكمال الطلب')
  assert(complete.data.user.needs_onboarding === false, 'needs_onboarding=false بعد الإكمال')
  assert(complete.data.user.status === 'reviewing', 'الحالة قيد المراجعة بعد الإكمال')
  assert(complete.data.mcq_answers.q1 === 'بكالوريوس', 'حفظ إجابات الاختيار')

  // 4) دخول لاحق لا يطلب onboarding
  const login2 = await call('/auth/user-login', 'POST', { code })
  assert(login2.data.user.needs_onboarding === false, 'لا onboarding بعد الإكمال')

  // 5) تفاصيل الطلب ظاهرة في get_user
  const details = await call(`/users/${codeUserId}`)
  assert(details.data.open_answers.q1 === 'هادئة وصادقة', 'تفاصيل الإجابات المفتوحة')
  assert(details.data.user.full_name === 'سارة أحمد', 'الاسم الحقيقي محفوظ')

  // 6) إنشاء إداري يحدّث admins.json
  const stamp = Date.now()
  const adminEmail = `admin.sync.${stamp}@wefaq.com`
  const adminLogin = await call('/auth/admin-login', 'POST', {
    email: 'super@wefaq.com',
    password: 'SuperAdmin@2026'
  })
  assert(adminLogin.data.success, 'دخول المدير العام')
  const superId = adminLogin.data.admin.id

  const createAdmin = await call('/admin/create', 'POST', {
    full_name: 'إداري مزامنة',
    phone: '0500999888',
    email: adminEmail,
    city: 'الدوحة',
    password: 'AdminSync@2026'
  })
  assert(createAdmin.status === 201, 'إنشاء إداري جديد')

  const adminsFileAfterCreate = readAdminsFile()
  assert(!adminsFileAfterCreate.super_admin.code, 'لا يوجد code في super_admin')
  assert(Array.isArray(adminsFileAfterCreate.admins), 'مصفوفة admins موجودة')
  const found = adminsFileAfterCreate.admins.find((a) => a.email === adminEmail)
  assert(found, 'الإداري الجديد موجود في admins.json')
  assert(found.password === 'AdminSync@2026', 'كلمة مرور الإداري محفوظة في الملف')
  assert(found.full_name === 'إداري مزامنة', 'اسم الإداري متزامن')

  // 7) حذف الإداري يزيله من الملف
  const del = await call(`/admin/admins/${createAdmin.data.admin_id}`, 'DELETE', { admin_id: superId })
  assert(del.data.success, 'حذف الإداري')
  const adminsFileAfterDelete = readAdminsFile()
  assert(
    !adminsFileAfterDelete.admins.find((a) => a.email === adminEmail),
    'الإداري حُذف من admins.json'
  )

  // 8) متتبع الخطوات (config) يحتوي 4 مراحل متسلسلة
  assert(config.registrationSteps.length === 4, 'عدد خطوات المتتبع = 4')
  assert(config.registrationSteps[0].key === 'personal', 'الخطوة الأولى: البيانات الشخصية')
  assert(config.registrationSteps[1].key === 'mcq', 'الخطوة الثانية: أسئلة الاختيار')
  assert(config.registrationSteps[2].key === 'open', 'الخطوة الثالثة: أسئلة مفتوحة')
  assert(config.registrationSteps[3].key === 'review', 'الخطوة الرابعة: المراجعة')

  console.log('\nجميع اختبارات onboarding ومزامنة الإداريين والمتتبع نجحت.')
}

run().catch((err) => {
  console.error('\nفشل الاختبار:', err.message)
  process.exit(1)
})
